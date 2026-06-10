"""Reconciliation tests for reusable analytics SQL views."""

from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine, text

from scripts.apply_sql_views import apply_sql_views


def _seed_metric_fixture(database_url: str):
    engine = create_engine(database_url)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE orders (
                order_id TEXT,
                customer_id TEXT,
                order_purchase_timestamp TEXT,
                order_delivered_customer_date TEXT,
                order_estimated_delivery_date TEXT,
                order_status TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE order_items (
                order_id TEXT,
                product_id TEXT,
                seller_id TEXT,
                price REAL,
                freight_value REAL
            )
        """))
        conn.execute(text("CREATE TABLE order_reviews (order_id TEXT, review_score INTEGER)"))
        conn.execute(text("""
            CREATE TABLE order_payments (
                order_id TEXT,
                payment_sequential INTEGER,
                payment_type TEXT,
                payment_installments INTEGER,
                payment_value REAL
            )
        """))
        conn.execute(text("""
            CREATE TABLE customers (
                customer_id TEXT,
                customer_unique_id TEXT,
                customer_state TEXT
            )
        """))
        conn.execute(text("CREATE TABLE sellers (seller_id TEXT, seller_state TEXT)"))
        conn.execute(text("""
            CREATE TABLE customer_segments (
                "Cluster" INTEGER,
                "Recency" REAL,
                "Frequency" REAL,
                "Monetary" REAL
            )
        """))

        conn.execute(text("""
            INSERT INTO orders VALUES
                ('o1', 'c1', '2024-01-01', '2024-01-05', '2024-01-06', 'delivered'),
                ('o2', 'c2', '2024-01-01', '2024-01-08', '2024-01-06', 'delivered'),
                ('o3', 'c3', '2024-02-10', '2024-02-15', '2024-02-18', 'delivered'),
                ('o4', 'c4', '2024-03-15', NULL, '2024-03-25', 'canceled')
        """))
        conn.execute(text("""
            INSERT INTO order_items VALUES
                ('o1', 'p1', 's1', 100.0, 10.0),
                ('o2', 'p2', 's1', 50.0, 5.0)
        """))
        conn.execute(text("INSERT INTO order_reviews VALUES ('o1', 5), ('o2', 2)"))
        conn.execute(text("""
            INSERT INTO order_payments VALUES
                ('o1', 1, 'credit_card', 1, 110.0),
                ('o2', 1, 'voucher', 1, 55.0)
        """))
        conn.execute(text("""
            INSERT INTO customers VALUES
                ('c1', 'u1', 'SP'),
                ('c2', 'u2', 'RJ'),
                ('c3', 'u1', 'SP'),
                ('c4', 'u4', 'MG')
        """))
        conn.execute(text("INSERT INTO sellers VALUES ('s1', 'SP')"))
        conn.execute(text("""
            INSERT INTO customer_segments VALUES
                (1, 10.0, 2.0, 50.0),
                (1, 20.0, 4.0, 100.0),
                (2, 60.0, 1.0, 20.0)
        """))
    return engine


def test_sql_views_reconcile_core_metrics(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'olist_metrics.db'}"
    engine = _seed_metric_fixture(database_url)

    applied, skipped = apply_sql_views(
        database_url=database_url,
        sql_dir=Path("sql/views"),
        strict=True,
    )

    assert skipped == []
    assert set(applied) == {
        "customer_segment_summary.sql",
        "customer_cohort_retention.sql",
        "delivery_quality.sql",
        "executive_order_summary.sql",
        "payment_mix_summary.sql",
        "review_delivery_drivers.sql",
        "seller_performance.sql",
        "seller_sla_summary.sql",
    }

    executive = pd.read_sql(
        text("SELECT * FROM executive_order_summary WHERE order_date = '2024-01-01'"),
        engine,
    ).iloc[0]
    assert executive["orders"] == 2
    assert executive["customers"] == 2
    assert executive["product_revenue"] == pytest.approx(150.0)
    assert executive["freight_revenue"] == pytest.approx(15.0)
    assert executive["avg_review_score"] == pytest.approx(3.5)

    delivery = pd.read_sql(
        text("SELECT SUM(is_late) AS late_orders FROM delivery_quality"),
        engine,
    ).iloc[0]
    assert delivery["late_orders"] == 1

    seller = pd.read_sql(text("SELECT * FROM seller_performance"), engine).iloc[0]
    assert seller["orders"] == 2
    assert seller["revenue"] == pytest.approx(150.0)
    assert seller["late_delivery_rate"] == pytest.approx(50.0)

    payment = pd.read_sql(
        text("SELECT * FROM payment_mix_summary WHERE payment_type = 'credit_card'"),
        engine,
    ).iloc[0]
    assert payment["orders"] == 1
    assert payment["payment_value"] == pytest.approx(110.0)

    review_driver = pd.read_sql(
        text("SELECT * FROM review_delivery_drivers WHERE review_score = 2"),
        engine,
    ).iloc[0]
    assert review_driver["orders"] == 1
    assert review_driver["late_delivery_rate"] == pytest.approx(100.0)

    seller_sla = pd.read_sql(text("SELECT * FROM seller_sla_summary"), engine).iloc[0]
    assert seller_sla["orders"] == 2
    assert seller_sla["items"] == 2
    assert seller_sla["product_revenue"] == pytest.approx(150.0)
    assert seller_sla["late_delivery_rate"] == pytest.approx(50.0)

    segment = pd.read_sql(
        text("SELECT * FROM customer_segment_summary WHERE segment_id = 1"),
        engine,
    ).iloc[0]
    assert segment["customers"] == 2
    assert segment["avg_monetary"] == pytest.approx(75.0)

    cohort_month_zero = pd.read_sql(
        text("""
            SELECT * FROM customer_cohort_retention
            WHERE cohort_month = '2024-01-01' AND months_since_first_order = 0
        """),
        engine,
    ).iloc[0]
    assert cohort_month_zero["cohort_customers"] == 2
    assert cohort_month_zero["active_customers"] == 2
    assert cohort_month_zero["orders"] == 2
    assert cohort_month_zero["retention_rate"] == pytest.approx(100.0)

    cohort_month_one = pd.read_sql(
        text("""
            SELECT * FROM customer_cohort_retention
            WHERE cohort_month = '2024-01-01' AND months_since_first_order = 1
        """),
        engine,
    ).iloc[0]
    assert cohort_month_one["cohort_customers"] == 2
    assert cohort_month_one["active_customers"] == 1
    assert cohort_month_one["orders"] == 1
    assert cohort_month_one["retention_rate"] == pytest.approx(50.0)


def test_apply_sql_views_can_replace_existing_view(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'replace_views.db'}"
    sql_dir = tmp_path / "sql"
    sql_dir.mkdir()
    sql_file = sql_dir / "example_view.sql"
    engine = create_engine(database_url)

    sql_file.write_text(
        "CREATE VIEW IF NOT EXISTS example_view AS SELECT 1 AS value",
        encoding="utf-8",
    )
    applied, skipped = apply_sql_views(database_url=database_url, sql_dir=sql_dir, strict=True)
    assert applied == ["example_view.sql"]
    assert skipped == []

    sql_file.write_text(
        "CREATE VIEW IF NOT EXISTS example_view AS SELECT 2 AS value",
        encoding="utf-8",
    )
    apply_sql_views(database_url=database_url, sql_dir=sql_dir, strict=True, replace=True)

    result = pd.read_sql(text("SELECT value FROM example_view"), engine).iloc[0, 0]
    assert result == 2
