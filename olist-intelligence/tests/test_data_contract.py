"""Tests for the Kaggle Olist source schema contract."""

from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from src.data_contract import (
    EXPECTED_CSV_SCHEMAS,
    EXPECTED_TABLE_SCHEMAS,
    expected_column_count,
    table_name_from_csv,
    validate_csv_directory,
    validate_database_schema,
)


def _write_csv(path: Path, columns: list[str]):
    path.write_text(",".join(columns) + "\n", encoding="utf-8")


def test_expected_schema_matches_kaggle_file_and_column_counts():
    assert len(EXPECTED_CSV_SCHEMAS) == 9
    assert expected_column_count() == 52


@pytest.mark.parametrize(
    ("file_name", "table_name"),
    [
        ("olist_orders_dataset.csv", "orders"),
        ("olist_order_items_dataset.csv", "order_items"),
        ("product_category_name_translation.csv", "product_category_name_translation"),
    ],
)
def test_table_name_from_csv_matches_ingestion_convention(file_name, table_name):
    assert table_name_from_csv(file_name) == table_name


def test_validate_csv_directory_accepts_expected_kaggle_headers(tmp_path):
    for file_name, columns in EXPECTED_CSV_SCHEMAS.items():
        _write_csv(tmp_path / file_name, columns)

    assert validate_csv_directory(tmp_path) == []


def test_validate_csv_directory_reports_missing_required_columns(tmp_path):
    for file_name, columns in EXPECTED_CSV_SCHEMAS.items():
        if file_name == "olist_orders_dataset.csv":
            columns = [column for column in columns if column != "order_status"]
        _write_csv(tmp_path / file_name, columns)

    issues = validate_csv_directory(tmp_path)

    assert any(
        issue.name == "olist_orders_dataset.csv"
        and issue.issue == "missing_columns"
        and "order_status" in issue.details
        for issue in issues
    )


def test_validate_database_schema_accepts_ingested_table_contract(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'olist_contract.db'}"
    engine = create_engine(database_url)

    with engine.begin() as conn:
        for table_name, columns in EXPECTED_TABLE_SCHEMAS.items():
            column_sql = ", ".join(f"{column} TEXT" for column in columns)
            conn.execute(text(f"CREATE TABLE {table_name} ({column_sql})"))

    assert validate_database_schema(database_url) == []


def test_validate_database_schema_does_not_create_missing_sqlite_file(tmp_path):
    db_path = tmp_path / "missing.db"
    issues = validate_database_schema(f"sqlite:///{db_path}")

    assert not db_path.exists()
    assert len(issues) == 1
    assert issues[0].issue == "missing_database"
