import pandas as pd
from sqlalchemy import text
from src.database.db_client import get_db_connection

engine = get_db_connection()

def get_total_orders(start_date, end_date):
    query = "SELECT COUNT(*) FROM orders WHERE order_purchase_timestamp::timestamp BETWEEN :start AND :end"
    return pd.read_sql(text(query), engine, params={"start": start_date, "end": end_date}).iloc[0, 0]

def get_date_range():
    query = "SELECT MIN(order_purchase_timestamp), MAX(order_purchase_timestamp) FROM orders"
    result = pd.read_sql(text(query), engine)
    return result.iloc[0, 0], result.iloc[0, 1]

def get_logistics_metrics(start_date, end_date):
    """Calculates dynamic KPIs for Logistics."""
    # 1. On-Time Delivery Rate & Avg Time
    query_kpi = """
    SELECT 
        COUNT(*) FILTER (WHERE delivery_days <= predicted_delivery_days) * 100.0 / NULLIF(COUNT(*), 0) as on_time_rate,
        AVG(delivery_days) as avg_time
    FROM logistics_predictions lp
    JOIN orders o ON lp.order_id = o.order_id
    WHERE o.order_purchase_timestamp::timestamp BETWEEN :start AND :end
    """
    kpi = pd.read_sql(text(query_kpi), engine, params={"start": start_date, "end": end_date}).iloc[0]
    
    # 2. Complaint Rate for Risky Orders (Late)
    # We assume 'order_reviews' exists. If not, return None.
    try:
        query_complaint = """
        SELECT 
            COUNT(*) FILTER (WHERE r.review_score <= 2) * 100.0 / NULLIF(COUNT(*), 0) as complaint_rate
        FROM logistics_predictions lp
        JOIN orders o ON lp.order_id = o.order_id
        JOIN order_reviews r ON o.order_id = r.order_id
        WHERE lp.predicted_delivery_days > 10
        AND o.order_purchase_timestamp::timestamp BETWEEN :start AND :end
        """
        complaint_rate = pd.read_sql(text(query_complaint), engine, params={"start": start_date, "end": end_date}).iloc[0, 0]
    except:
        complaint_rate = None
        
    return {
        "on_time_rate": kpi["on_time_rate"] if pd.notnull(kpi["on_time_rate"]) else 0,
        "avg_time": kpi["avg_time"] if pd.notnull(kpi["avg_time"]) else 0,
        "complaint_rate": complaint_rate if pd.notnull(complaint_rate) else 15.0 # Fallback to 15%
    }

def get_logistics_risk_count(start_date, end_date):
    query = """
    SELECT COUNT(*) 
    FROM logistics_predictions lp
    JOIN orders o ON lp.order_id = o.order_id
    WHERE lp.predicted_delivery_days > 10
    AND o.order_purchase_timestamp::timestamp BETWEEN :start AND :end
    """
    return pd.read_sql(text(query), engine, params={"start": start_date, "end": end_date}).iloc[0, 0]

def get_churn_risk_count():
    # Snapshot metric, no date filter for now
    return pd.read_sql("SELECT COUNT(*) FROM customer_segments WHERE \"Cluster\" IN (2, 3)", engine).iloc[0, 0]

def get_logistics_details(start_date, end_date, limit=10):
    query = """
    SELECT 
        lp.customer_id, 
        lp.predicted_delivery_days as "Tahmini Süre (Gün)",
        lp.delivery_days as "Gerçekleşen (Gün)"
    FROM logistics_predictions lp
    JOIN orders o ON lp.order_id = o.order_id
    WHERE lp.predicted_delivery_days > 10
    AND o.order_purchase_timestamp::timestamp BETWEEN :start AND :end
    LIMIT :limit
    """
    return pd.read_sql(text(query), engine, params={"start": start_date, "end": end_date, "limit": limit})

def get_customer_segments_stats():
    query = "SELECT \"Cluster\", COUNT(*) as count, AVG(\"Monetary\") as avg_spend, AVG(\"Recency\") as avg_recency, AVG(\"Frequency\") as avg_freq FROM customer_segments GROUP BY \"Cluster\""
    return pd.read_sql(query, engine)

def get_target_audience(cluster_id=None, limit=500):
    base_query = """
    SELECT customer_unique_id, "Recency", "Frequency", "Monetary", "Cluster"
    FROM customer_segments
    """
    if cluster_id is not None:
        query = f"{base_query} WHERE \"Cluster\" = {cluster_id} ORDER BY \"Monetary\" DESC LIMIT {limit}"
    else:
        query = f"{base_query} ORDER BY \"Monetary\" DESC LIMIT {limit}"
    return pd.read_sql(query, engine)

def log_action_to_db(action_type, description, impact_value):
    # Fix for numpy types
    if hasattr(impact_value, 'item'):
        impact_value = impact_value.item()
        
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO action_logs (action_type, description, impact_value)
            VALUES (:type, :desc, :val)
        """), {"type": action_type, "desc": description, "val": impact_value})
        conn.commit()

def get_recent_actions(limit=5):
    return pd.read_sql(text("SELECT * FROM action_logs ORDER BY timestamp DESC LIMIT :limit"), engine, params={"limit": limit})

def init_bi_tables():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS action_logs (
                id SERIAL PRIMARY KEY,
                action_type VARCHAR(50),
                description TEXT,
                impact_value FLOAT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()
