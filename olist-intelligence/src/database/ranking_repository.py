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


def _window_params(start_date, end_date, limit=None):
    params = {
        "start_date": start_date,
        "end_date": end_date,
    }
    if limit is not None:
        params["limit"] = limit
    return params


def get_top_products(limit=20, start_date=None, end_date=None):
    """Return top product categories by revenue."""
    limit = clamp_limit(limit, default=20)
    query = text("""
    SELECT
        COALESCE(t.product_category_name_english, p.product_category_name, 'Other') AS product_category,
        COUNT(DISTINCT oi.order_id) AS order_count,
        SUM(oi.price) AS total_sales
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    JOIN orders o ON oi.order_id = o.order_id
    LEFT JOIN product_category_name_translation t
        ON p.product_category_name = t.product_category_name
    WHERE (:start_date IS NULL OR DATE(o.order_purchase_timestamp) >= DATE(:start_date))
      AND (:end_date IS NULL OR DATE(o.order_purchase_timestamp) <= DATE(:end_date))
    GROUP BY product_category
    ORDER BY total_sales DESC
    LIMIT :limit
    """)

    try:
        df = pd.read_sql(
            query,
            engine,
            params=_window_params(start_date, end_date, limit),
        )
    except Exception:
        return empty_frame(TOP_PRODUCT_COLUMNS)

    if df.empty:
        return empty_frame(TOP_PRODUCT_COLUMNS)

    return df[TOP_PRODUCT_COLUMNS]


def get_top_sellers(limit=20, start_date=None, end_date=None):
    """Return delivered-order seller performance ranked by revenue."""
    limit = clamp_limit(limit, default=20)
    query = text("""
    SELECT
        s.seller_id,
        COUNT(DISTINCT oi.order_id) AS order_count,
        SUM(oi.price) AS total_revenue,
        AVG(r.review_score) AS avg_rating,
        SUM(
            CASE
                WHEN DATE(o.order_delivered_customer_date) <= DATE(o.order_estimated_delivery_date)
                THEN 1 ELSE 0
            END
        ) AS on_time_count,
        COUNT(oi.order_id) AS total_rows,
        SUM(
            CASE
                WHEN DATE(o.order_delivered_customer_date) <= DATE(o.order_estimated_delivery_date)
                THEN 1 ELSE 0
            END
        ) * 100.0 / COUNT(oi.order_id) AS on_time_rate
    FROM sellers s
    JOIN order_items oi ON s.seller_id = oi.seller_id
    JOIN orders o ON oi.order_id = o.order_id
    LEFT JOIN order_reviews r ON o.order_id = r.order_id
    WHERE o.order_status = 'delivered'
      AND (:start_date IS NULL OR DATE(o.order_purchase_timestamp) >= DATE(:start_date))
      AND (:end_date IS NULL OR DATE(o.order_purchase_timestamp) <= DATE(:end_date))
    GROUP BY s.seller_id
    HAVING COUNT(DISTINCT oi.order_id) >= 5
    ORDER BY total_revenue DESC
    LIMIT :limit
    """)

    try:
        df = pd.read_sql(
            query,
            engine,
            params=_window_params(start_date, end_date, limit),
        )
    except Exception:
        return empty_frame(TOP_SELLER_COLUMNS)

    if df.empty:
        return empty_frame(TOP_SELLER_COLUMNS)

    return df[TOP_SELLER_COLUMNS]


def get_category_performance(start_date=None, end_date=None):
    """Return delivered-order category revenue, review, and order metrics."""
    query = text("""
    SELECT
        COALESCE(t.product_category_name_english, p.product_category_name, 'Other') AS category,
        SUM(oi.price) AS revenue,
        AVG(r.review_score) AS avg_review,
        COUNT(DISTINCT oi.order_id) AS order_count
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    JOIN orders o ON oi.order_id = o.order_id
    LEFT JOIN order_reviews r ON o.order_id = r.order_id
    LEFT JOIN product_category_name_translation t
        ON p.product_category_name = t.product_category_name
    WHERE o.order_status = 'delivered'
      AND (:start_date IS NULL OR DATE(o.order_purchase_timestamp) >= DATE(:start_date))
      AND (:end_date IS NULL OR DATE(o.order_purchase_timestamp) <= DATE(:end_date))
    GROUP BY category
    HAVING SUM(oi.price) > 1000
    ORDER BY revenue DESC
    LIMIT 30
    """)

    try:
        df = pd.read_sql(query, engine, params=_window_params(start_date, end_date))
    except Exception:
        return empty_frame(CATEGORY_PERFORMANCE_COLUMNS)

    if df.empty:
        return empty_frame(CATEGORY_PERFORMANCE_COLUMNS)

    return df[CATEGORY_PERFORMANCE_COLUMNS]
