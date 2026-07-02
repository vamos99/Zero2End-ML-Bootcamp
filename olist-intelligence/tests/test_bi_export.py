from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine, text

from scripts.export_bi_marts import MartExport, export_bi_marts


def _create_empty_database(database_url: str):
    engine = create_engine(database_url)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE placeholder (id INTEGER)"))


def test_export_bi_marts_writes_csv_and_manifest(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'bi.db'}"
    engine = create_engine(database_url)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE VIEW payment_mix_summary AS
            SELECT
                '2017-01-01' AS order_date,
                'credit_card' AS payment_type,
                2 AS orders,
                3 AS payment_records,
                120.5 AS payment_value,
                2.0 AS avg_installments
        """))

    manifest = export_bi_marts(
        database_url,
        tmp_path / "exports",
        marts=[
            MartExport(
                name="payment_mix_summary",
                source_name="payment_mix_summary",
                file_name="payment_mix_summary.csv",
                description="Payment mix.",
                order_by="order_date, payment_type",
            )
        ],
    )

    output_path = Path(manifest["exports"][0]["path"])
    exported = pd.read_csv(output_path)

    assert manifest["status"] == "ok"
    assert manifest["exports"][0]["status"] == "exported"
    assert manifest["exports"][0]["rows"] == 1
    assert output_path.name == "payment_mix_summary.csv"
    assert exported.iloc[0]["payment_type"] == "credit_card"
    assert "Unnamed: 0" not in exported.columns
    assert (tmp_path / "exports" / "manifest.json").exists()


def test_export_bi_marts_skips_missing_views_by_default(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'bi.db'}"
    _create_empty_database(database_url)

    manifest = export_bi_marts(
        database_url,
        tmp_path / "exports",
        marts=[
            MartExport(
                name="missing_mart",
                source_name="missing_mart",
                file_name="missing_mart.csv",
                description="Missing mart.",
            )
        ],
    )

    assert manifest["status"] == "partial"
    assert manifest["exports"][0]["status"] == "skipped"
    assert "Missing source relation" in manifest["exports"][0]["reason"]
    assert (tmp_path / "exports" / "manifest.json").exists()


def test_export_bi_marts_strict_missing_view_raises(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'bi.db'}"
    _create_empty_database(database_url)

    with pytest.raises(RuntimeError, match="Missing source relation"):
        export_bi_marts(
            database_url,
            tmp_path / "exports",
            marts=[
                MartExport(
                    name="missing_mart",
                    source_name="missing_mart",
                    file_name="missing_mart.csv",
                    description="Missing mart.",
                )
            ],
            strict=True,
        )


def test_export_bi_marts_does_not_create_missing_sqlite_database(tmp_path):
    missing_db = tmp_path / "missing.db"

    with pytest.raises(FileNotFoundError, match="Run ingestion before BI export"):
        export_bi_marts(f"sqlite:///{missing_db}", tmp_path / "exports")

    assert not missing_db.exists()
