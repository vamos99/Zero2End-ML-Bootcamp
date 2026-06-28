import pandas as pd
from sqlalchemy import inspect, text
from src.database.dataframe_factory import empty_frame
from src.database.db_client import get_db_connection
from src.database.query_limits import clamp_limit
from src.database.repository_columns import (
    COHORT_RETENTION_COLUMNS,
    PAYMENT_MIX_COLUMNS,
    REVENUE_BY_STATE_COLUMNS,
    REVIEW_DELIVERY_MATRIX_COLUMNS,
    SELLER_SLA_COLUMNS,
)
from src.database.repository_defaults import (
    EMPTY_REVIEW_DELIVERY,
    EMPTY_SOURCE_BASELINES,
    EMPTY_TOTALS,
)
from src.database import action_repository, customer_repository, logistics_repository, ranking_repository

engine = get_db_connection()


def get_generated_output_status():
    """Report whether notebook/model-generated dashboard tables are available."""
    table_names = set(inspect(engine).get_table_names())
    return {
        "logistics_predictions": "logistics_predictions" in table_names,
        "customer_segments": "customer_segments" in table_names,
    }


def get_total_orders(start_date, end_date):
    query = text("""
    SELECT COUNT(DISTINCT order_id)
    FROM orders
    WHERE DATE(order_purchase_timestamp) BETWEEN DATE(:start_date) AND DATE(:end_date)
    """)
    try:
        return int(
            pd.read_sql(
                query,
                engine,
                params={"start_date": start_date, "end_date": end_date},
            ).iloc[0, 0]
        )
    except Exception:
        return 0

def get_date_range():
    query = "SELECT MIN(order_purchase_timestamp), MAX(order_purchase_timestamp) FROM orders"
    # This standard SQL works on both SQLite and Postgres
    result = pd.read_sql(text(query), engine)
    return result.iloc[0, 0], result.iloc[0, 1]

def get_revenue_metrics(start_date, end_date):
    """Returns executive revenue metrics for the selected order window."""
    query = text("""
    WITH order_value AS (
        SELECT
            order_id,
            SUM(price) AS product_revenue,
            SUM(freight_value) AS freight_revenue
        FROM order_items
        GROUP BY order_id
    )
    SELECT
        o.order_id,
        o.customer_id,
        COALESCE(ov.product_revenue, 0) AS product_revenue,
        COALESCE(ov.freight_revenue, 0) AS freight_revenue
    FROM orders o
    LEFT JOIN order_value ov ON o.order_id = ov.order_id
    WHERE DATE(o.order_purchase_timestamp) BETWEEN DATE(:start_date) AND DATE(:end_date)
    """)

    try:
        df = pd.read_sql(query, engine, params={"start_date": start_date, "end_date": end_date})
    except Exception:
        return EMPTY_TOTALS.copy()

    if df.empty:
        return EMPTY_TOTALS.copy()

    total_orders = df["order_id"].nunique()
    unique_customers = df["customer_id"].nunique()
    total_revenue = float(df["product_revenue"].sum())

    return {
        "total_revenue": total_revenue,
        "avg_order_value": total_revenue / total_orders if total_orders else 0.0,
        "unique_customers": int(unique_customers),
        "revenue_per_customer": total_revenue / unique_customers if unique_customers else 0.0,
    }

def get_review_delivery_quality(start_date, end_date):
    """Summarizes review and delivery quality for the selected order window."""
    query = text("""
    SELECT
        o.order_id,
        o.order_delivered_customer_date,
        o.order_estimated_delivery_date,
        r.review_score,
        CASE
            WHEN o.order_delivered_customer_date IS NULL THEN NULL
            WHEN o.order_estimated_delivery_date IS NULL THEN NULL
            WHEN DATE(o.order_delivered_customer_date) > DATE(o.order_estimated_delivery_date) THEN 1
            ELSE 0
        END AS is_late
    FROM orders o
    LEFT JOIN order_reviews r ON o.order_id = r.order_id
    WHERE DATE(o.order_purchase_timestamp) BETWEEN DATE(:start_date) AND DATE(:end_date)
    """)

    try:
        df = pd.read_sql(query, engine, params={"start_date": start_date, "end_date": end_date})
    except Exception:
        return EMPTY_REVIEW_DELIVERY.copy()

    if df.empty:
        return EMPTY_REVIEW_DELIVERY.copy()

    delivered = df[df["is_late"].notna()]

    return {
        "avg_review_score": float(df["review_score"].dropna().mean()) if df["review_score"].notna().any() else 0.0,
        "late_delivery_rate": float(delivered["is_late"].mean() * 100) if not delivered.empty else 0.0,
        "review_count": int(df["review_score"].notna().sum()),
    }


def get_source_business_baselines():
    """Returns source-snapshot baselines used for impact scenario planning."""
    delivery_query = text("""
    SELECT
        CASE
            WHEN DATE(order_delivered_customer_date) > DATE(order_estimated_delivery_date)
            THEN 1 ELSE 0
        END AS is_late,
        CASE
            WHEN DATE(order_delivered_customer_date) > DATE(order_estimated_delivery_date)
            THEN JULIANDAY(DATE(order_delivered_customer_date))
               - JULIANDAY(DATE(order_estimated_delivery_date))
            ELSE 0
        END AS days_late
    FROM orders
    WHERE order_status = 'delivered'
      AND order_delivered_customer_date IS NOT NULL
      AND order_estimated_delivery_date IS NOT NULL
      AND JULIANDAY(order_delivered_customer_date) > JULIANDAY(order_purchase_timestamp)
    """)
    repeat_query = text("""
    SELECT
        c.customer_unique_id,
        COUNT(DISTINCT o.order_id) AS delivered_orders
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id
    """)

    try:
        delivery = pd.read_sql(delivery_query, engine)
        repeat = pd.read_sql(repeat_query, engine)
    except Exception:
        return {
            "delivery": EMPTY_SOURCE_BASELINES["delivery"].copy(),
            "repeat_purchase": EMPTY_SOURCE_BASELINES["repeat_purchase"].copy(),
        }

    if delivery.empty or repeat.empty:
        return {
            "delivery": EMPTY_SOURCE_BASELINES["delivery"].copy(),
            "repeat_purchase": EMPTY_SOURCE_BASELINES["repeat_purchase"].copy(),
        }

    is_late = delivery["is_late"] == 1
    repeat_customers = repeat["delivered_orders"] > 1
    avg_days_late = delivery.loc[is_late, "days_late"].mean() if is_late.any() else 0.0

    return {
        "delivery": {
            "delivered_orders": int(len(delivery)),
            "late_orders": int(is_late.sum()),
            "late_delivery_rate_pct": float(is_late.mean() * 100),
            "avg_days_late_when_late": float(avg_days_late),
        },
        "repeat_purchase": {
            "unique_customers": int(len(repeat)),
            "repeat_customers": int(repeat_customers.sum()),
            "one_time_customers": int((~repeat_customers).sum()),
            "repeat_customer_rate_pct": float(repeat_customers.mean() * 100),
            "one_time_customer_rate_pct": float((~repeat_customers).mean() * 100),
        },
    }

def get_revenue_by_state(start_date, end_date, limit=12):
    """Returns customer-state revenue ranking for the executive dashboard."""
    limit = clamp_limit(limit, default=12)
    query = text("""
    WITH order_value AS (
        SELECT
            order_id,
            SUM(price) AS product_revenue
        FROM order_items
        GROUP BY order_id
    )
    SELECT
        c.customer_state,
        COUNT(DISTINCT o.order_id) AS order_count,
        SUM(COALESCE(ov.product_revenue, 0)) AS revenue
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    LEFT JOIN order_value ov ON o.order_id = ov.order_id
    WHERE DATE(o.order_purchase_timestamp) BETWEEN DATE(:start_date) AND DATE(:end_date)
    GROUP BY c.customer_state
    ORDER BY revenue DESC
    LIMIT :limit
    """)

    try:
        return pd.read_sql(
            query,
            engine,
            params={"start_date": start_date, "end_date": end_date, "limit": limit},
        )
    except Exception:
        return empty_frame(REVENUE_BY_STATE_COLUMNS)

def get_review_delivery_matrix(start_date, end_date):
    """Returns review-score delivery quality for a simple driver chart."""
    query = text("""
    SELECT
        r.review_score,
        COUNT(DISTINCT o.order_id) AS order_count,
        AVG(
            CASE
                WHEN o.order_delivered_customer_date IS NULL THEN NULL
                WHEN o.order_estimated_delivery_date IS NULL THEN NULL
                WHEN DATE(o.order_delivered_customer_date) > DATE(o.order_estimated_delivery_date) THEN 1.0
                ELSE 0.0
            END
        ) * 100 AS late_delivery_rate
    FROM orders o
    JOIN order_reviews r ON o.order_id = r.order_id
    WHERE DATE(o.order_purchase_timestamp) BETWEEN DATE(:start_date) AND DATE(:end_date)
    GROUP BY r.review_score
    ORDER BY r.review_score
    """)

    try:
        return pd.read_sql(query, engine, params={"start_date": start_date, "end_date": end_date})
    except Exception:
        return empty_frame(REVIEW_DELIVERY_MATRIX_COLUMNS)

def get_payment_mix_summary(start_date, end_date, limit=6):
    """Returns payment-method mix from the reusable payment mart."""
    limit = clamp_limit(limit, default=6)
    query = text("""
    SELECT
        payment_type,
        SUM(orders) AS orders,
        SUM(payment_records) AS payment_records,
        SUM(payment_value) AS payment_value,
        SUM(avg_installments * payment_records) / NULLIF(SUM(payment_records), 0) AS avg_installments
    FROM payment_mix_summary
    WHERE order_date BETWEEN DATE(:start_date) AND DATE(:end_date)
    GROUP BY payment_type
    ORDER BY payment_value DESC
    LIMIT :limit
    """)

    try:
        return pd.read_sql(
            query,
            engine,
            params={"start_date": start_date, "end_date": end_date, "limit": limit},
        )
    except Exception:
        return empty_frame(PAYMENT_MIX_COLUMNS)

def get_cohort_retention_matrix(start_date, end_date, max_cohorts=8, max_months=6, min_cohort_size=100):
    """Returns recent customer cohort retention rows for a dashboard heatmap."""
    max_cohorts = clamp_limit(max_cohorts, default=8)
    max_months = clamp_limit(max_months, default=6)
    query = text("""
    WITH selected_cohorts AS (
        SELECT cohort_month
        FROM customer_cohort_retention
        WHERE months_since_first_order = 0
            AND cohort_customers >= :min_cohort_size
            AND cohort_month BETWEEN DATE(:start_date, 'start of month') AND DATE(:end_date, 'start of month')
        ORDER BY cohort_month DESC
        LIMIT :max_cohorts
    )
    SELECT
        STRFTIME('%Y-%m', c.cohort_month) AS cohort_month,
        c.months_since_first_order,
        c.cohort_customers,
        c.active_customers,
        c.retention_rate
    FROM customer_cohort_retention c
    JOIN selected_cohorts sc ON c.cohort_month = sc.cohort_month
    WHERE c.months_since_first_order BETWEEN 0 AND :max_months
    ORDER BY c.cohort_month DESC, c.months_since_first_order
    """)

    try:
        return pd.read_sql(
            query,
            engine,
            params={
                "start_date": start_date,
                "end_date": end_date,
                "max_cohorts": max_cohorts,
                "max_months": max_months,
                "min_cohort_size": min_cohort_size,
            },
        )
    except Exception:
        return empty_frame(COHORT_RETENTION_COLUMNS)

def get_seller_sla_watchlist(limit=10, min_orders=20):
    """Returns sellers with enough delivered orders and high SLA risk."""
    limit = clamp_limit(limit, default=10)
    query = text("""
    SELECT
        seller_id,
        seller_state,
        orders,
        product_revenue,
        avg_review_score,
        avg_delivery_days,
        late_delivery_rate
    FROM seller_sla_summary
    WHERE orders >= :min_orders
    ORDER BY late_delivery_rate DESC, product_revenue DESC
    LIMIT :limit
    """)

    try:
        return pd.read_sql(query, engine, params={"limit": limit, "min_orders": min_orders})
    except Exception:
        return empty_frame(SELLER_SLA_COLUMNS)

def get_logistics_metrics(start_date, end_date):
    """Backward-compatible facade for logistics metrics."""
    return logistics_repository.get_logistics_metrics(start_date, end_date)


def get_logistics_risk_count(start_date, end_date):
    """Backward-compatible facade for logistics risk counts."""
    return logistics_repository.get_logistics_risk_count(start_date, end_date)


def get_logistics_details(start_date, end_date, limit=10):
    """Backward-compatible facade for logistics detail rows."""
    return logistics_repository.get_logistics_details(start_date, end_date, limit)


def get_churn_risk_count():
    """Backward-compatible facade for the relative At Risk segment count."""
    return customer_repository.get_churn_risk_count()


def get_customer_segments_stats():
    """Backward-compatible facade for generated segment summaries."""
    return customer_repository.get_customer_segments_stats()


def get_target_audience(segment_name=None, limit=500):
    """Backward-compatible facade for target-audience exports."""
    return customer_repository.get_target_audience(segment_name, limit)

def log_action_to_db(action_type, description, impact_value):
    """Backward-compatible facade for action logging."""
    return action_repository.log_action_to_db(action_type, description, impact_value)

def get_recent_actions(limit=5):
    """Backward-compatible facade for recent actions."""
    return action_repository.get_recent_actions(limit)

def init_bi_tables():
    """Backward-compatible facade for action table initialization."""
    return action_repository.init_bi_tables()

def get_top_products(limit=20, start_date=None, end_date=None):
    """Backward-compatible facade for product category rankings."""
    return ranking_repository.get_top_products(limit, start_date, end_date)

def get_top_sellers(limit=20, start_date=None, end_date=None):
    """Backward-compatible facade for seller rankings."""
    return ranking_repository.get_top_sellers(limit, start_date, end_date)

def get_category_performance(start_date=None, end_date=None):
    """Backward-compatible facade for category performance."""
    return ranking_repository.get_category_performance(start_date, end_date)


def get_random_customer_id():
    """Backward-compatible facade for dashboard customer sampling."""
    return customer_repository.get_random_customer_id()
