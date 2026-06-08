"""Source schema contract for the Kaggle Olist dataset.

The raw CSV files are not committed to the repository. This module keeps the
expected file, table, and column contract close to the ingestion code so local
data loads can be validated before dashboard or model work starts.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url


KAGGLE_DATASET = "olistbr/brazilian-ecommerce"
KAGGLE_DATASET_URL = "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce"

EXPECTED_CSV_SCHEMAS: dict[str, list[str]] = {
    "olist_customers_dataset.csv": [
        "customer_id",
        "customer_unique_id",
        "customer_zip_code_prefix",
        "customer_city",
        "customer_state",
    ],
    "olist_geolocation_dataset.csv": [
        "geolocation_zip_code_prefix",
        "geolocation_lat",
        "geolocation_lng",
        "geolocation_city",
        "geolocation_state",
    ],
    "olist_order_items_dataset.csv": [
        "order_id",
        "order_item_id",
        "product_id",
        "seller_id",
        "shipping_limit_date",
        "price",
        "freight_value",
    ],
    "olist_order_payments_dataset.csv": [
        "order_id",
        "payment_sequential",
        "payment_type",
        "payment_installments",
        "payment_value",
    ],
    "olist_order_reviews_dataset.csv": [
        "review_id",
        "order_id",
        "review_score",
        "review_comment_title",
        "review_comment_message",
        "review_creation_date",
        "review_answer_timestamp",
    ],
    "olist_orders_dataset.csv": [
        "order_id",
        "customer_id",
        "order_status",
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "olist_products_dataset.csv": [
        "product_id",
        "product_category_name",
        "product_name_lenght",
        "product_description_lenght",
        "product_photos_qty",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    ],
    "olist_sellers_dataset.csv": [
        "seller_id",
        "seller_zip_code_prefix",
        "seller_city",
        "seller_state",
    ],
    "product_category_name_translation.csv": [
        "product_category_name",
        "product_category_name_english",
    ],
}


def table_name_from_csv(file_name: str) -> str:
    """Match OlistIngestor's CSV-to-table naming convention."""
    return file_name.replace("olist_", "").replace("_dataset.csv", "").replace(".csv", "")


EXPECTED_TABLE_SCHEMAS: dict[str, list[str]] = {
    table_name_from_csv(file_name): columns
    for file_name, columns in EXPECTED_CSV_SCHEMAS.items()
}


@dataclass(frozen=True)
class SchemaIssue:
    scope: str
    name: str
    issue: str
    details: str


def expected_column_count() -> int:
    return sum(len(columns) for columns in EXPECTED_CSV_SCHEMAS.values())


def _read_csv_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.reader(file)
        return next(reader, [])


def _compare_columns(
    scope: str,
    name: str,
    expected: list[str],
    actual: list[str],
    strict_extra: bool,
) -> list[SchemaIssue]:
    issues: list[SchemaIssue] = []
    missing = [column for column in expected if column not in actual]
    extra = [column for column in actual if column not in expected]

    if missing:
        issues.append(SchemaIssue(scope, name, "missing_columns", ", ".join(missing)))

    if strict_extra and extra:
        issues.append(SchemaIssue(scope, name, "extra_columns", ", ".join(extra)))

    return issues


def validate_csv_directory(data_path: Path, strict_extra: bool = False) -> list[SchemaIssue]:
    """Validate raw Kaggle CSV headers in a local data directory."""
    issues: list[SchemaIssue] = []

    for file_name, expected_columns in EXPECTED_CSV_SCHEMAS.items():
        path = data_path / file_name
        if not path.exists():
            issues.append(SchemaIssue("csv", file_name, "missing_file", str(path)))
            continue

        actual_columns = _read_csv_header(path)
        issues.extend(
            _compare_columns(
                scope="csv",
                name=file_name,
                expected=expected_columns,
                actual=actual_columns,
                strict_extra=strict_extra,
            )
        )

    return issues


def validate_database_schema(database_url: str, strict_extra: bool = False) -> list[SchemaIssue]:
    """Validate ingested Olist tables and columns in SQLite/Postgres-compatible databases."""
    url = make_url(database_url)
    if url.drivername.startswith("sqlite") and url.database not in {None, "", ":memory:"}:
        database_path = Path(url.database)
        if not database_path.exists():
            return [
                SchemaIssue(
                    "db",
                    "database",
                    "missing_database",
                    str(database_path),
                )
            ]

    engine = create_engine(database_url)
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    issues: list[SchemaIssue] = []

    for table_name, expected_columns in EXPECTED_TABLE_SCHEMAS.items():
        if table_name not in table_names:
            issues.append(SchemaIssue("db", table_name, "missing_table", table_name))
            continue

        actual_columns = [column["name"] for column in inspector.get_columns(table_name)]
        issues.extend(
            _compare_columns(
                scope="db",
                name=table_name,
                expected=expected_columns,
                actual=actual_columns,
                strict_extra=strict_extra,
            )
        )

    return issues
