"""Logistics dashboard queries and stable fallback contracts."""

import pandas as pd
from sqlalchemy import text

from src.database.dataframe_factory import empty_frame
from src.database.db_client import get_db_connection
from src.database.query_limits import clamp_limit
from src.database.repository_columns import LOGISTICS_DETAILS_COLUMNS


engine = get_db_connection()


def get_logistics_metrics(start_date, end_date):
    query = text("""
    SELECT
        CAST(JULIANDAY(o.order_delivered_customer_date) - JULIANDAY(o.order_purchase_timestamp) AS INTEGER) AS delivery_days,
        lp.predicted_delivery_days,
        r.review_score
    FROM logistics_predictions lp
    JOIN orders o ON lp.order_id = o.order_id
    LEFT JOIN order_reviews r ON o.order_id = r.order_id
    WHERE DATE(o.order_purchase_timestamp) BETWEEN DATE(:start_date) AND DATE(:end_date)
    """)
    try:
        frame = pd.read_sql(
            query,
            engine,
            params={"start_date": start_date, "end_date": end_date},
        )
    except Exception:
        return {"available": False, "on_time_rate": 0, "avg_time": 0, "low_review_rate": 0}

    if frame.empty:
        return {"available": True, "on_time_rate": 0, "avg_time": 0, "low_review_rate": 0}

    on_time_rate = (
        len(frame[frame["delivery_days"] <= frame["predicted_delivery_days"]])
        / len(frame)
        * 100
    )
    risky_orders = frame[frame["predicted_delivery_days"] > 10]
    low_review_rate = (
        len(risky_orders[risky_orders["review_score"] <= 2]) / len(risky_orders) * 100
        if not risky_orders.empty
        else 0.0
    )
    return {
        "available": True,
        "on_time_rate": on_time_rate,
        "avg_time": frame["delivery_days"].mean(),
        "low_review_rate": low_review_rate,
    }


def get_logistics_risk_count(start_date, end_date):
    query = text("""
    SELECT COUNT(*)
    FROM logistics_predictions lp
    JOIN orders o ON lp.order_id = o.order_id
    WHERE lp.predicted_delivery_days > 10
      AND DATE(o.order_purchase_timestamp) BETWEEN DATE(:start_date) AND DATE(:end_date)
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


def get_logistics_details(start_date, end_date, limit=10):
    limit = clamp_limit(limit, default=10)
    query = text("""
    SELECT
        o.customer_id,
        lp.predicted_delivery_days AS "Tahmini Süre (Gün)",
        CAST(JULIANDAY(o.order_delivered_customer_date) - JULIANDAY(o.order_purchase_timestamp) AS INTEGER) AS "Gerçekleşen (Gün)",
        o.order_purchase_timestamp
    FROM logistics_predictions lp
    JOIN orders o ON lp.order_id = o.order_id
    WHERE lp.predicted_delivery_days > 10
      AND DATE(o.order_purchase_timestamp) BETWEEN DATE(:start_date) AND DATE(:end_date)
    ORDER BY lp.predicted_delivery_days DESC
    LIMIT :limit
    """)
    try:
        frame = pd.read_sql(
            query,
            engine,
            params={"start_date": start_date, "end_date": end_date, "limit": limit},
        )
    except Exception:
        return empty_frame(LOGISTICS_DETAILS_COLUMNS)
    return frame.drop(columns=["order_purchase_timestamp"])
