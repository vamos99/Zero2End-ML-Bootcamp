"""Focused ingestion failure and skip-behavior tests."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest
from sqlalchemy import create_engine, text

from src.ml.ingest import OlistIngestor, reconcile_ingestion_manifest


MANIFEST_ROW = {
    "file_name": "olist_orders_dataset.csv",
    "table_name": "orders",
    "source_rows": 1,
    "db_rows": 1,
    "missing_columns": [],
    "status": "loaded",
}


def test_get_csv_files_fails_when_download_does_not_produce_contract(tmp_path, monkeypatch):
    ingestor = OlistIngestor(f"sqlite:///{tmp_path / 'olist.db'}", str(tmp_path / "raw"))
    monkeypatch.setattr(ingestor, "download_from_kaggle", lambda: None)

    with pytest.raises(FileNotFoundError):
        ingestor.get_csv_files()


def test_ingest_file_propagates_parser_failure(tmp_path, monkeypatch):
    source = tmp_path / "olist_orders_dataset.csv"
    source.write_text("broken", encoding="utf-8")
    ingestor = OlistIngestor(f"sqlite:///{tmp_path / 'olist.db'}", str(tmp_path))
    monkeypatch.setattr("src.ml.ingest.pl.read_csv", MagicMock(side_effect=ValueError("bad csv")))

    with pytest.raises(ValueError, match="bad csv"):
        ingestor.ingest_file(str(source))


def test_ingest_file_returns_manifest_row_counts(tmp_path):
    source = tmp_path / "raw" / "olist_orders_dataset.csv"
    source.parent.mkdir()
    columns = [
        "order_id",
        "customer_id",
        "order_status",
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    source.write_text(
        "\n".join([
            ",".join(columns),
            "o1,c1,delivered,2017-01-01,2017-01-01,2017-01-02,2017-01-03,2017-01-05",
        ]),
        encoding="utf-8",
    )
    ingestor = OlistIngestor(f"sqlite:///{tmp_path / 'olist.db'}", str(tmp_path / "raw"))

    result = ingestor.ingest_file(str(source))

    assert result == {
        "file_name": "olist_orders_dataset.csv",
        "table_name": "orders",
        "source_rows": 1,
        "db_rows": 1,
        "missing_columns": [],
        "status": "loaded",
    }


def test_write_manifest_and_reconcile_row_counts(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    database_url = f"sqlite:///{tmp_path / 'olist.db'}"
    engine = create_engine(database_url)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE orders (order_id TEXT)"))
        conn.execute(text("INSERT INTO orders VALUES ('o1')"))

    ingestor = OlistIngestor(database_url, str(tmp_path / "raw"), manifest_path=str(manifest_path))
    written_path = ingestor.write_ingestion_manifest([
        {
            "file_name": "olist_orders_dataset.csv",
            "table_name": "orders",
            "source_rows": 1,
            "db_rows": 1,
            "missing_columns": [],
            "status": "loaded",
        }
    ])

    manifest = json.loads(written_path.read_text(encoding="utf-8"))
    result = reconcile_ingestion_manifest(database_url, manifest_path)

    assert manifest["status"] == "success"
    assert manifest["database_target"] == {"database": "olist.db", "driver": "sqlite"}
    assert result["status"] == "ok"
    assert result["checked_tables"] == 1
    assert result["issues"] == []


def test_reconcile_manifest_reports_row_count_mismatch(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    database_url = f"sqlite:///{tmp_path / 'olist.db'}"
    engine = create_engine(database_url)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE orders (order_id TEXT)"))
        conn.execute(text("INSERT INTO orders VALUES ('o1')"))

    manifest_path.write_text(
        json.dumps({
            "run_id": "test-run",
            "tables": [{"table_name": "orders", "source_rows": 2}],
        }),
        encoding="utf-8",
    )

    result = reconcile_ingestion_manifest(database_url, manifest_path)

    assert result["status"] == "failed"
    assert result["issues"] == [
        {
            "table_name": "orders",
            "source_rows": 2,
            "db_rows": 1,
            "issue": "row_count_mismatch",
        }
    ]


def test_existing_database_is_skipped_only_after_schema_validation(tmp_path, monkeypatch):
    database_path = tmp_path / "olist.db"
    database_path.write_text("existing", encoding="utf-8")
    ingestor = OlistIngestor(
        f"sqlite:///{database_path}",
        str(tmp_path / "raw"),
        manifest_path=str(tmp_path / "manifest.json"),
    )
    monkeypatch.setattr("src.ml.ingest.validate_database_schema", lambda _url: [])
    get_csv_files = MagicMock()
    monkeypatch.setattr(ingestor, "get_csv_files", get_csv_files)

    ingestor.run()

    get_csv_files.assert_not_called()
    assert not ingestor.manifest_path.exists()


def test_force_ingest_bypasses_existing_database_skip(tmp_path, monkeypatch):
    database_path = tmp_path / "olist.db"
    database_path.write_text("existing", encoding="utf-8")
    source = tmp_path / "raw" / "olist_orders_dataset.csv"
    source.parent.mkdir()
    source.write_text("order_id\n1\n", encoding="utf-8")
    ingestor = OlistIngestor(
        f"sqlite:///{database_path}",
        str(tmp_path / "raw"),
        manifest_path=str(tmp_path / "manifest.json"),
    )
    monkeypatch.setenv("FORCE_INGEST", "1")
    monkeypatch.setattr(ingestor, "get_csv_files", MagicMock(return_value=[str(source)]))
    monkeypatch.setattr(ingestor, "ingest_file", MagicMock(return_value=MANIFEST_ROW))
    monkeypatch.setattr("src.ml.ingest.validate_database_quality", lambda _url: [])
    monkeypatch.setattr(ingestor, "load_predictions_from_csv", MagicMock())

    ingestor.run()

    ingestor.get_csv_files.assert_called_once()
    ingestor.ingest_file.assert_called_once_with(str(source))
    ingestor.load_predictions_from_csv.assert_called_once()
    assert ingestor.manifest_path.exists()


def test_invalid_existing_database_is_rebuilt(tmp_path, monkeypatch):
    database_path = tmp_path / "olist.db"
    database_path.write_text("existing", encoding="utf-8")
    source = tmp_path / "raw" / "olist_orders_dataset.csv"
    source.parent.mkdir()
    source.write_text("order_id\n1\n", encoding="utf-8")
    ingestor = OlistIngestor(
        f"sqlite:///{database_path}",
        str(tmp_path / "raw"),
        manifest_path=str(tmp_path / "manifest.json"),
    )
    monkeypatch.delenv("FORCE_INGEST", raising=False)
    monkeypatch.setattr("src.ml.ingest.validate_database_schema", lambda _url: ["missing table"])
    monkeypatch.setattr(ingestor, "get_csv_files", MagicMock(return_value=[str(source)]))
    monkeypatch.setattr(ingestor, "ingest_file", MagicMock(return_value=MANIFEST_ROW))
    monkeypatch.setattr("src.ml.ingest.validate_database_quality", lambda _url: [])
    monkeypatch.setattr(ingestor, "load_predictions_from_csv", MagicMock())

    ingestor.run()

    ingestor.get_csv_files.assert_called_once()
    ingestor.ingest_file.assert_called_once_with(str(source))
    assert ingestor.manifest_path.exists()


def test_static_generated_outputs_are_loaded_when_present(tmp_path):
    project_root = tmp_path / "project"
    data_raw = project_root / "data" / "raw"
    processed = project_root / "data" / "processed"
    processed.mkdir(parents=True)
    data_raw.mkdir(parents=True)
    database_url = f"sqlite:///{project_root / 'olist.db'}"
    pd.DataFrame(
        {
            "order_id": ["o1"],
            "predicted_delivery_days": [12.5],
        }
    ).to_csv(processed / "logistics_predictions.csv", index=False)
    pd.DataFrame(
        {
            "customer_unique_id": ["u1"],
            "Cluster": [1],
            "Segment": ["Loyal"],
        }
    ).to_csv(processed / "customer_segments.csv", index=False)

    ingestor = OlistIngestor(database_url, str(data_raw))
    ingestor.project_root = project_root
    ingestor.load_predictions_from_csv()

    engine = create_engine(database_url)
    with engine.connect() as conn:
        logistics_count = conn.execute(text("SELECT COUNT(*) FROM logistics_predictions")).scalar_one()
        segments_count = conn.execute(text("SELECT COUNT(*) FROM customer_segments")).scalar_one()

    assert logistics_count == 1
    assert segments_count == 1
