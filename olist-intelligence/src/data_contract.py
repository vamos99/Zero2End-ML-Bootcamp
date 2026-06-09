"""Source schema contract for the Kaggle Olist dataset.

The raw CSV files are not committed to the repository. This module keeps the
expected file, table, and column contract close to the ingestion code so local
data loads can be validated before dashboard or model work starts.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
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

PRIMARY_KEY_CHECKS: dict[str, list[str]] = {
    "orders": ["order_id"],
    "customers": ["customer_id"],
    "sellers": ["seller_id"],
    "products": ["product_id"],
    "product_category_name_translation": ["product_category_name"],
    "order_items": ["order_id", "order_item_id"],
    "order_payments": ["order_id", "payment_sequential"],
}

REQUIRED_COLUMNS: dict[str, list[str]] = {
    "orders": ["order_id", "customer_id", "order_purchase_timestamp", "order_status"],
    "order_items": ["order_id", "order_item_id", "product_id", "seller_id", "price", "freight_value"],
    "order_payments": ["order_id", "payment_type", "payment_value"],
    "order_reviews": ["order_id", "review_score"],
    "customers": ["customer_id", "customer_unique_id"],
    "sellers": ["seller_id"],
    "products": ["product_id"],
}

REFERENTIAL_CHECKS: list[tuple[str, str, str, str]] = [
    ("orders", "customer_id", "customers", "customer_id"),
    ("order_items", "order_id", "orders", "order_id"),
    ("order_items", "product_id", "products", "product_id"),
    ("order_items", "seller_id", "sellers", "seller_id"),
    ("order_payments", "order_id", "orders", "order_id"),
    ("order_reviews", "order_id", "orders", "order_id"),
]

ACCEPTED_ORDER_STATUSES = {
    "approved",
    "canceled",
    "created",
    "delivered",
    "invoiced",
    "processing",
    "shipped",
    "unavailable",
}

ACCEPTED_PAYMENT_TYPES = {
    "boleto",
    "credit_card",
    "debit_card",
    "not_defined",
    "voucher",
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


def _format_columns(columns: list[str]) -> str:
    return ", ".join(columns)


def _sql_string_list(values: set[str]) -> str:
    quoted = [f"'{value}'" for value in sorted(values)]
    return ", ".join(quoted)


def _count_query(conn, statement: str, params: dict | None = None) -> int:
    return int(conn.execute(text(statement), params or {}).scalar_one())


def _validate_required_tables_have_rows(conn) -> list[SchemaIssue]:
    issues: list[SchemaIssue] = []
    for table_name in EXPECTED_TABLE_SCHEMAS:
        row_count = _count_query(conn, f"SELECT COUNT(*) FROM {table_name}")
        if row_count == 0:
            issues.append(
                SchemaIssue(
                    "quality",
                    table_name,
                    "empty_table",
                    "expected at least one row after a full Kaggle load",
                )
            )
    return issues


def _validate_required_column_completeness(conn) -> list[SchemaIssue]:
    issues: list[SchemaIssue] = []
    for table_name, columns in REQUIRED_COLUMNS.items():
        for column in columns:
            missing_count = _count_query(
                conn,
                f"SELECT COUNT(*) FROM {table_name} WHERE {column} IS NULL",
            )
            if missing_count:
                issues.append(
                    SchemaIssue(
                        "quality",
                        table_name,
                        "null_required_column",
                        f"{column}: {missing_count} rows",
                    )
                )
    return issues


def _validate_primary_keys(conn) -> list[SchemaIssue]:
    issues: list[SchemaIssue] = []
    for table_name, columns in PRIMARY_KEY_CHECKS.items():
        column_list = _format_columns(columns)
        duplicate_groups = _count_query(
            conn,
            f"""
            SELECT COUNT(*) FROM (
                SELECT {column_list}
                FROM {table_name}
                GROUP BY {column_list}
                HAVING COUNT(*) > 1
            ) duplicate_keys
            """,
        )
        if duplicate_groups:
            issues.append(
                SchemaIssue(
                    "quality",
                    table_name,
                    "duplicate_key",
                    f"{column_list}: {duplicate_groups} duplicated key groups",
                )
            )
    return issues


def _validate_referential_integrity(conn) -> list[SchemaIssue]:
    issues: list[SchemaIssue] = []
    for child_table, child_key, parent_table, parent_key in REFERENTIAL_CHECKS:
        orphan_count = _count_query(
            conn,
            f"""
            SELECT COUNT(*)
            FROM {child_table} child
            LEFT JOIN {parent_table} parent
                ON child.{child_key} = parent.{parent_key}
            WHERE child.{child_key} IS NOT NULL
                AND parent.{parent_key} IS NULL
            """,
        )
        if orphan_count:
            issues.append(
                SchemaIssue(
                    "quality",
                    child_table,
                    "orphan_foreign_key",
                    f"{child_key} -> {parent_table}.{parent_key}: {orphan_count} rows",
                )
            )
    return issues


def _validate_domain_rules(conn) -> list[SchemaIssue]:
    issues: list[SchemaIssue] = []

    invalid_statuses = _count_query(
        conn,
        f"""
        SELECT COUNT(*)
        FROM orders
        WHERE order_status IS NOT NULL
            AND order_status NOT IN ({_sql_string_list(ACCEPTED_ORDER_STATUSES)})
        """,
    )
    if invalid_statuses:
        issues.append(
            SchemaIssue("quality", "orders", "invalid_order_status", f"{invalid_statuses} rows")
        )

    invalid_payment_types = _count_query(
        conn,
        f"""
        SELECT COUNT(*)
        FROM order_payments
        WHERE payment_type IS NOT NULL
            AND payment_type NOT IN ({_sql_string_list(ACCEPTED_PAYMENT_TYPES)})
        """,
    )
    if invalid_payment_types:
        issues.append(
            SchemaIssue(
                "quality",
                "order_payments",
                "invalid_payment_type",
                f"{invalid_payment_types} rows",
            )
        )

    invalid_reviews = _count_query(
        conn,
        """
        SELECT COUNT(*)
        FROM order_reviews
        WHERE review_score IS NOT NULL
            AND (review_score < 1 OR review_score > 5)
        """,
    )
    if invalid_reviews:
        issues.append(
            SchemaIssue("quality", "order_reviews", "invalid_review_score", f"{invalid_reviews} rows")
        )

    negative_item_values = _count_query(
        conn,
        """
        SELECT COUNT(*)
        FROM order_items
        WHERE price < 0 OR freight_value < 0
        """,
    )
    if negative_item_values:
        issues.append(
            SchemaIssue(
                "quality",
                "order_items",
                "negative_item_value",
                f"{negative_item_values} rows",
            )
        )

    negative_payment_values = _count_query(
        conn,
        """
        SELECT COUNT(*)
        FROM order_payments
        WHERE payment_value < 0 OR payment_installments < 0
        """,
    )
    if negative_payment_values:
        issues.append(
            SchemaIssue(
                "quality",
                "order_payments",
                "negative_payment_value",
                f"{negative_payment_values} rows",
            )
        )

    impossible_delivery_dates = _count_query(
        conn,
        """
        SELECT COUNT(*)
        FROM orders
        WHERE order_delivered_customer_date IS NOT NULL
            AND order_purchase_timestamp IS NOT NULL
            AND order_delivered_customer_date < order_purchase_timestamp
        """,
    )
    if impossible_delivery_dates:
        issues.append(
            SchemaIssue(
                "quality",
                "orders",
                "delivered_before_purchase",
                f"{impossible_delivery_dates} rows",
            )
        )

    return issues


def validate_database_quality(database_url: str) -> list[SchemaIssue]:
    """Run stable data-quality checks after the Olist schema has been loaded."""
    schema_issues = validate_database_schema(database_url)
    if schema_issues:
        return schema_issues

    engine = create_engine(database_url)
    issues: list[SchemaIssue] = []
    with engine.connect() as conn:
        issues.extend(_validate_required_tables_have_rows(conn))
        issues.extend(_validate_required_column_completeness(conn))
        issues.extend(_validate_primary_keys(conn))
        issues.extend(_validate_referential_integrity(conn))
        issues.extend(_validate_domain_rules(conn))

    return issues
