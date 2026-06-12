import pandas as pd
from sqlalchemy import text

from src.database.db_client import get_db_connection

engine = get_db_connection()


def get_top_products(limit=10):
    query = text("""
    SELECT
        p.product_category_name,
        COUNT(oi.order_id) AS order_count,
        SUM(oi.price) AS total_revenue
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    GROUP BY p.product_category_name
    ORDER BY total_revenue DESC
    LIMIT :limit
    """)

    try:
        return pd.read_sql(query, engine, params={"limit": limit})
    except Exception:
        return pd.DataFrame(columns=["product_category_name", "order_count", "total_revenue"])
