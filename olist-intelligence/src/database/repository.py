import pandas as pd
from sqlalchemy import text
from src.database.dataframe_factory import empty_frame
from src.database.db_client import get_db_connection
from src.database.query_limits import clamp_limit
from src.database.repository_columns import (
    COHORT_RETENTION_COLUMNS,
    PAYMENT_MIX_COLUMNS,
    REVENUE_BY_STATE_COLUMNS,
    REVIEW_DELIVERY_MATRIX_COLUMNS,
)
from src.database.repository_defaults import EMPTY_REVIEW_DELIVERY, EMPTY_TOTALS
from src.database import ranking_repository

engine = get_db_connection()

def get_total_orders(start_date, end_date):
    query = "SELECT order_purchase_timestamp FROM orders"
    df = pd.read_sql(text(query), engine)
    df['order_purchase_timestamp'] = pd.to_datetime(df['order_purchase_timestamp'])
    
    mask = (df['order_purchase_timestamp'] >= pd.to_datetime(start_date)) & \
           (df['order_purchase_timestamp'] <= pd.to_datetime(end_date))
    
    return len(df[mask])

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
            WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 1
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
                WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 1.0
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
        return pd.DataFrame(
            columns=[
                "seller_id",
                "seller_state",
                "orders",
                "product_revenue",
                "avg_review_score",
                "avg_delivery_days",
                "late_delivery_rate",
            ]
        )

def get_logistics_metrics(start_date, end_date):
    """Calculates dynamic KPIs for Logistics (DB Agnostic)."""
    # 1. Fetch Raw Data needed for KPIs
    query = """
    SELECT 
        CAST(JULIANDAY(o.order_delivered_customer_date) - JULIANDAY(o.order_purchase_timestamp) AS INTEGER) as delivery_days,
        lp.predicted_delivery_days,
        o.order_purchase_timestamp,
        r.review_score
    FROM logistics_predictions lp
    JOIN orders o ON lp.order_id = o.order_id
    LEFT JOIN order_reviews r ON o.order_id = r.order_id
    """
    
    try:
        df = pd.read_sql(text(query), engine)
    except Exception as e:
        # Table might not exist yet
        return {"on_time_rate": 0, "avg_time": 0, "complaint_rate": 0}
        
    if df.empty:
         return {"on_time_rate": 0, "avg_time": 0, "complaint_rate": 0}

    # 2. Process in Python
    df['order_purchase_timestamp'] = pd.to_datetime(df['order_purchase_timestamp'])
    mask = (df['order_purchase_timestamp'] >= pd.to_datetime(start_date)) & \
           (df['order_purchase_timestamp'] <= pd.to_datetime(end_date))
    
    filtered = df[mask]
    
    if filtered.empty:
        return {"on_time_rate": 0, "avg_time": 0, "complaint_rate": 0}

    # KPI 1: On-Time Rate
    on_time = filtered[filtered['delivery_days'] <= filtered['predicted_delivery_days']]
    on_time_rate = (len(on_time) / len(filtered)) * 100
    
    # KPI 2: Avg Time
    avg_time = filtered['delivery_days'].mean()
    
    # KPI 3: Risky Orders Complaint Rate
    risky_orders = filtered[filtered['predicted_delivery_days'] > 10]
    if not risky_orders.empty:
        complaints = risky_orders[risky_orders['review_score'] <= 2]
        complaint_rate = (len(complaints) / len(risky_orders)) * 100
    else:
        complaint_rate = 0.0

    return {
        "on_time_rate": on_time_rate,
        "avg_time": avg_time,
        "complaint_rate": complaint_rate
    }

def get_logistics_risk_count(start_date, end_date):
    query = """
    SELECT lp.predicted_delivery_days, o.order_purchase_timestamp
    FROM logistics_predictions lp
    JOIN orders o ON lp.order_id = o.order_id
    """
    try:
        df = pd.read_sql(text(query), engine)
    except:
        return 0
        
    if df.empty: return 0
    
    df['order_purchase_timestamp'] = pd.to_datetime(df['order_purchase_timestamp'])
    
    # Filter
    mask = (df['order_purchase_timestamp'] >= pd.to_datetime(start_date)) & \
           (df['order_purchase_timestamp'] <= pd.to_datetime(end_date)) & \
           (df['predicted_delivery_days'] > 10)
           
    return len(df[mask])

def get_churn_risk_count():
    # Snapshot metric, no date filter for now
    try:
        return pd.read_sql("SELECT COUNT(*) FROM customer_segments WHERE \"Cluster\" IN (2, 3)", engine).iloc[0, 0]
    except:
        return 0

def get_logistics_details(start_date, end_date, limit=10):
    query = text("""
    SELECT 
        o.customer_id, 
        lp.predicted_delivery_days as "Tahmini Süre (Gün)",
        CAST(JULIANDAY(o.order_delivered_customer_date) - JULIANDAY(o.order_purchase_timestamp) AS INTEGER) as "Gerçekleşen (Gün)",
        o.order_purchase_timestamp
    FROM logistics_predictions lp
    JOIN orders o ON lp.order_id = o.order_id
    WHERE lp.predicted_delivery_days > 10
    LIMIT 50
    """)
    
    try:
        df = pd.read_sql(query, engine)
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch logistics details (Table missing?): {e}")
        # Return empty DF with expected columns to prevent UI crash
        return pd.DataFrame(columns=["customer_id", "Tahmini Süre (Gün)", "Gerçekleşen (Gün)", "order_purchase_timestamp"])
        
    df['order_purchase_timestamp'] = pd.to_datetime(df['order_purchase_timestamp'])
    
    mask = (df['order_purchase_timestamp'] >= pd.to_datetime(start_date)) & \
           (df['order_purchase_timestamp'] <= pd.to_datetime(end_date))
           
    res = df[mask].head(limit)
    return res.drop(columns=['order_purchase_timestamp'])

def get_customer_segments_stats():
    query = "SELECT \"Cluster\", COUNT(*) as count, AVG(\"Monetary\") as avg_spend, AVG(\"Recency\") as avg_recency, AVG(\"Frequency\") as avg_freq FROM customer_segments GROUP BY \"Cluster\""
    try:
        return pd.read_sql(query, engine)
    except Exception:
        return pd.DataFrame()

def get_target_audience(cluster_id=None, limit=500):
    base_query = """
    SELECT customer_unique_id, "Recency", "Frequency", "Monetary", "Cluster"
    FROM customer_segments
    """
    if cluster_id is not None:
        query = f"{base_query} WHERE \"Cluster\" = :cluster_id ORDER BY \"Monetary\" DESC LIMIT :limit"
        params = {"cluster_id": cluster_id, "limit": limit}
    else:
        query = f"{base_query} ORDER BY \"Monetary\" DESC LIMIT :limit"
        params = {"limit": limit}
    
    try:
        return pd.read_sql(text(query), engine, params=params)
    except Exception:
        return pd.DataFrame(columns=["customer_unique_id", "Recency", "Frequency", "Monetary", "Cluster"])

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
    dialect = engine.dialect.name
    
    if dialect == 'sqlite':
        id_col = "id INTEGER PRIMARY KEY AUTOINCREMENT"
        timestamp_col = "timestamp DATETIME DEFAULT CURRENT_TIMESTAMP"
    else:
        # PostgreSQL
        id_col = "id SERIAL PRIMARY KEY"
        timestamp_col = "timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        
    create_sql = f"""
            CREATE TABLE IF NOT EXISTS action_logs (
                {id_col},
                action_type VARCHAR(50),
                description TEXT,
                impact_value FLOAT,
                {timestamp_col}
            )
    """
    
    with engine.connect() as conn:
        conn.execute(text(create_sql))
        conn.commit()

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
    try:
        return pd.read_sql('SELECT customer_unique_id FROM customers ORDER BY RANDOM() LIMIT 1', engine).iloc[0, 0]
    except:
        return '871766c5855e863f6eccc05f988b23'
