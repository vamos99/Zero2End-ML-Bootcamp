import pandas as pd
from sqlalchemy import text

from src.database.dataframe_factory import empty_frame
from src.database.db_client import get_db_connection
from src.database.query_limits import clamp_limit
from src.database.ranking_schema import (
    CATEGORY_PERFORMANCE_COLUMNS,
    TOP_PRODUCT_COLUMNS,
    TOP_SELLER_COLUMNS,
)

engine = get_db_connection()


def _filter_order_window(df, start_date, end_date):
    if not start_date or not end_date:
        return df

    order_dates = pd.to_datetime(df["order_purchase_timestamp"])
    return df[
        (order_dates >= pd.to_datetime(start_date))
        & (order_dates <= pd.to_datetime(end_date))
    ]


def get_top_products(limit=20, start_date=None, end_date=None):
    """Return top product categories by revenue."""
    limit = clamp_limit(limit, default=20)
    query = text("""
    SELECT
        COALESCE(t.product_category_name_english, p.product_category_name, 'Other') AS product_category,
        oi.order_id,
        oi.price,
        o.order_purchase_timestamp
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    JOIN orders o ON oi.order_id = o.order_id
    LEFT JOIN product_category_name_translation t
        ON p.product_category_name = t.product_category_name
    """)

    try:
        df = _filter_order_window(pd.read_sql(query, engine), start_date, end_date)
    except Exception:
        return empty_frame(TOP_PRODUCT_COLUMNS)

    if df.empty:
        return empty_frame(TOP_PRODUCT_COLUMNS)

    return (
        df.groupby("product_category")
        .agg(order_count=("order_id", "nunique"), total_sales=("price", "sum"))
        .reset_index()
        .sort_values("total_sales", ascending=False)
        .head(limit)
    )


def get_top_sellers(limit=20, start_date=None, end_date=None):
    """Return delivered-order seller performance ranked by revenue."""
    limit = clamp_limit(limit, default=20)
    query = text("""
    SELECT
        s.seller_id,
        oi.order_id,
        oi.price,
        r.review_score,
        o.order_delivered_customer_date,
        o.order_estimated_delivery_date,
        o.order_purchase_timestamp
    FROM sellers s
    JOIN order_items oi ON s.seller_id = oi.seller_id
    JOIN orders o ON oi.order_id = o.order_id
    LEFT JOIN order_reviews r ON o.order_id = r.order_id
    WHERE o.order_status = 'delivered'
    """)

    try:
        df = _filter_order_window(pd.read_sql(query, engine), start_date, end_date)
    except Exception:
        return empty_frame(TOP_SELLER_COLUMNS)

    if df.empty:
        return empty_frame(TOP_SELLER_COLUMNS)

    delivered = pd.to_datetime(df["order_delivered_customer_date"])
    estimated = pd.to_datetime(df["order_estimated_delivery_date"])
    df = df.assign(is_on_time=delivered <= estimated)

    result = (
        df.groupby("seller_id")
        .agg(
            order_count=("order_id", "nunique"),
            total_revenue=("price", "sum"),
            avg_rating=("review_score", "mean"),
            on_time_count=("is_on_time", "sum"),
            total_rows=("order_id", "count"),
        )
        .reset_index()
    )
    result["on_time_rate"] = result["on_time_count"] / result["total_rows"] * 100
    return (
        result[result["order_count"] >= 5]
        .sort_values("total_revenue", ascending=False)
        .head(limit)
    )


def get_category_performance(start_date=None, end_date=None):
    """Return delivered-order category revenue, review, and order metrics."""
    query = text("""
    SELECT
        COALESCE(t.product_category_name_english, p.product_category_name, 'Other') AS category,
        oi.price,
        r.review_score,
        oi.order_id,
        o.order_purchase_timestamp
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    JOIN orders o ON oi.order_id = o.order_id
    LEFT JOIN order_reviews r ON o.order_id = r.order_id
    LEFT JOIN product_category_name_translation t
        ON p.product_category_name = t.product_category_name
    WHERE o.order_status = 'delivered'
    """)

    try:
        df = _filter_order_window(pd.read_sql(query, engine), start_date, end_date)
    except Exception:
        return empty_frame(CATEGORY_PERFORMANCE_COLUMNS)

    if df.empty:
        return empty_frame(CATEGORY_PERFORMANCE_COLUMNS)

    result = (
        df.groupby("category")
        .agg(
            revenue=("price", "sum"),
            avg_review=("review_score", "mean"),
            order_count=("order_id", "nunique"),
        )
        .reset_index()
    )
    return result[result["revenue"] > 1000].sort_values("revenue", ascending=False).head(30)
