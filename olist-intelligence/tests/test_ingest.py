"""Focused ingestion failure and skip-behavior tests."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.ml.ingest import OlistIngestor


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


def test_existing_database_is_skipped_only_after_schema_validation(tmp_path, monkeypatch):
    database_path = tmp_path / "olist.db"
    database_path.write_text("existing", encoding="utf-8")
    ingestor = OlistIngestor(f"sqlite:///{database_path}", str(tmp_path / "raw"))
    monkeypatch.setattr("src.ml.ingest.validate_database_schema", lambda _url: [])
    get_csv_files = MagicMock()
    monkeypatch.setattr(ingestor, "get_csv_files", get_csv_files)

    ingestor.run()

    get_csv_files.assert_not_called()
