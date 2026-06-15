"""Customer segmentation queries and stable fallback contracts."""

import pandas as pd
from sqlalchemy import text

from src.database.dataframe_factory import empty_frame
from src.database.db_client import get_db_connection
from src.database.query_limits import clamp_limit
from src.database.repository_columns import TARGET_AUDIENCE_COLUMNS


engine = get_db_connection()


def get_churn_risk_count():
    """Count the generated relative segment labeled At Risk."""
    try:
        query = text("""
        SELECT COUNT(*)
        FROM customer_segments
        WHERE LOWER("Segment") LIKE :segment
        """)
        return int(pd.read_sql(query, engine, params={"segment": "%at risk%"}).iloc[0, 0])
    except Exception:
        return 0


def get_customer_segments_stats():
    query = """
    SELECT
        "Cluster",
        "Segment",
        COUNT(*) AS count,
        AVG("Monetary") AS avg_spend,
        AVG("Recency") AS avg_recency,
        AVG("Frequency") AS avg_freq
    FROM customer_segments
    GROUP BY "Cluster", "Segment"
    """
    try:
        return pd.read_sql(query, engine)
    except Exception:
        return pd.DataFrame()


def get_target_audience(segment_name=None, limit=500):
    limit = clamp_limit(limit, default=100, maximum=500)
    base_query = """
    SELECT customer_unique_id, "Recency", "Frequency", "Monetary", "Cluster", "Segment"
    FROM customer_segments
    """
    if segment_name is not None:
        query = f'{base_query} WHERE "Segment" = :segment_name ORDER BY "Monetary" DESC LIMIT :limit'
        params = {"segment_name": segment_name, "limit": limit}
    else:
        query = f'{base_query} ORDER BY "Monetary" DESC LIMIT :limit'
        params = {"limit": limit}
    try:
        return pd.read_sql(text(query), engine, params=params)
    except Exception:
        return empty_frame(TARGET_AUDIENCE_COLUMNS)


def get_random_customer_id():
    try:
        return pd.read_sql(
            "SELECT customer_unique_id FROM customers ORDER BY RANDOM() LIMIT 1",
            engine,
        ).iloc[0, 0]
    except Exception:
        return "871766c5855e863f6eccc05f988b23"
