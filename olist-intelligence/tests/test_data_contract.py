"""Tests for the Kaggle Olist source schema contract."""

from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from src.data_contract import (
    EXPECTED_CSV_SCHEMAS,
    EXPECTED_TABLE_SCHEMAS,
    GENERATED_TABLE_SCHEMAS,
    expected_column_count,
    table_name_from_csv,
    validate_csv_directory,
    validate_database_quality,
    validate_database_schema,
    validate_generated_outputs,
)


def _write_csv(path: Path, columns: list[str]):
    path.write_text(",".join(columns) + "\n", encoding="utf-8")


def _column_type(column: str) -> str:
    if column in {
        "price",
        "freight_value",
        "payment_value",
        "geolocation_lat",
        "geolocation_lng",
    }:
        return "REAL"
    if column in {
        "order_item_id",
        "payment_sequential",
        "payment_installments",
        "review_score",
        "customer_zip_code_prefix",
        "seller_zip_code_prefix",
        "geolocation_zip_code_prefix",
        "product_name_lenght",
        "product_description_lenght",
        "product_photos_qty",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    }:
        return "INTEGER"
    return "TEXT"


def _create_expected_tables(engine):
    with engine.begin() as conn:
        for table_name, columns in EXPECTED_TABLE_SCHEMAS.items():
            column_sql = ", ".join(f"{column} {_column_type(column)}" for column in columns)
            conn.execute(text(f"CREATE TABLE {table_name} ({column_sql})"))


def _seed_valid_olist_contract(engine):
    _create_expected_tables(engine)
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO customers VALUES
                ('c1', 'u1', 1000, 'sao paulo', 'SP')
        """))
        conn.execute(text("""
            INSERT INTO geolocation VALUES
                (1000, -23.5, -46.6, 'sao paulo', 'SP')
        """))
        conn.execute(text("""
            INSERT INTO sellers VALUES
                ('s1', 1000, 'sao paulo', 'SP')
        """))
        conn.execute(text("""
            INSERT INTO products VALUES
                ('p1', 'cat1', 10, 20, 1, 500, 10, 10, 10)
        """))
        conn.execute(text("""
            INSERT INTO product_category_name_translation VALUES
                ('cat1', 'category one')
        """))
        conn.execute(text("""
            INSERT INTO orders VALUES
                (
                    'o1', 'c1', 'delivered', '2017-01-01',
                    '2017-01-01', '2017-01-02', '2017-01-03', '2017-01-05'
                )
        """))
        conn.execute(text("""
            INSERT INTO order_items VALUES
                ('o1', 1, 'p1', 's1', '2017-01-02', 100.0, 10.0)
        """))
        conn.execute(text("""
            INSERT INTO order_payments VALUES
                ('o1', 1, 'credit_card', 1, 110.0)
        """))
        conn.execute(text("""
            INSERT INTO order_reviews VALUES
                ('r1', 'o1', 5, 'ok', 'good', '2017-01-04', '2017-01-05')
        """))


def test_expected_schema_matches_kaggle_file_and_column_counts():
    assert len(EXPECTED_CSV_SCHEMAS) == 9
    assert expected_column_count() == 52
    assert set(GENERATED_TABLE_SCHEMAS) == {"logistics_predictions", "customer_segments"}


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


def test_validate_csv_directory_accepts_utf8_sig_header(tmp_path):
    for file_name, columns in EXPECTED_CSV_SCHEMAS.items():
        content = ",".join(columns) + "\n"
        if file_name == "product_category_name_translation.csv":
            (tmp_path / file_name).write_text(content, encoding="utf-8-sig")
        else:
            (tmp_path / file_name).write_text(content, encoding="utf-8")

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


def test_validate_database_quality_accepts_valid_minimal_fixture(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'olist_quality.db'}"
    engine = create_engine(database_url)
    _seed_valid_olist_contract(engine)

    assert validate_database_quality(database_url) == []


def test_validate_database_quality_reports_duplicate_and_orphan_keys(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'olist_quality.db'}"
    engine = create_engine(database_url)
    _seed_valid_olist_contract(engine)

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO orders VALUES
                (
                    'o1', 'c1', 'delivered', '2017-01-02',
                    '2017-01-02', '2017-01-03', '2017-01-04', '2017-01-06'
                )
        """))
        conn.execute(text("""
            INSERT INTO order_items VALUES
                ('missing_order', 1, 'missing_product', 's1', '2017-01-02', 50.0, 5.0)
        """))

    issues = validate_database_quality(database_url)

    assert any(issue.issue == "duplicate_key" and issue.name == "orders" for issue in issues)
    assert any(issue.issue == "orphan_foreign_key" and issue.name == "order_items" for issue in issues)


def test_validate_database_quality_reports_domain_rule_violations(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'olist_quality.db'}"
    engine = create_engine(database_url)
    _seed_valid_olist_contract(engine)

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO orders VALUES
                (
                    'o_bad', 'c1', 'returned', '2017-01-10',
                    '2017-01-10', '2017-01-11', '2017-01-09', '2017-01-15'
                )
        """))
        conn.execute(text("""
            INSERT INTO order_items VALUES
                ('o_bad', 1, 'p1', 's1', '2017-01-11', -10.0, 5.0)
        """))
        conn.execute(text("""
            INSERT INTO order_payments VALUES
                ('o_bad', 1, 'crypto', 1, -20.0)
        """))
        conn.execute(text("""
            INSERT INTO order_reviews VALUES
                ('r_bad', 'o_bad', 6, 'bad', 'bad', '2017-01-12', '2017-01-13')
        """))

    issue_names = {issue.issue for issue in validate_database_quality(database_url)}

    assert "invalid_order_status" in issue_names
    assert "delivered_before_purchase" in issue_names
    assert "negative_item_value" in issue_names
    assert "invalid_payment_type" in issue_names
    assert "negative_payment_value" in issue_names
    assert "invalid_review_score" in issue_names


def test_validate_generated_outputs_accepts_dashboard_contract(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'generated.db'}"
    engine = create_engine(database_url)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE logistics_predictions (
                order_id TEXT,
                customer_id TEXT,
                predicted_delivery_days REAL,
                delivery_days REAL,
                prediction_source TEXT
            )
        """))
        conn.execute(text("""
            INSERT INTO logistics_predictions VALUES ('o1', 'c1', 5.0, 4.0, 'baseline')
        """))
        conn.execute(text("""
            CREATE TABLE customer_segments (
                customer_unique_id TEXT,
                "Recency" REAL,
                "Frequency" REAL,
                "Monetary" REAL,
                "Cluster" INTEGER,
                "Segment" TEXT
            )
        """))
        conn.execute(text("""
            INSERT INTO customer_segments VALUES ('u1', 10, 2, 100, 0, 'At Risk')
        """))

    assert validate_generated_outputs(database_url) == []


def test_validate_generated_outputs_reports_missing_tables(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'generated.db'}"
    create_engine(database_url)

    issues = validate_generated_outputs(database_url)

    assert {issue.name for issue in issues} == {
        "logistics_predictions",
        "customer_segments",
    }
