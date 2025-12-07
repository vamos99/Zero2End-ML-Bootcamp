import pandas as pd
from sqlalchemy import text
from src.database.db_client import get_db_connection

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

# ============== NEW: RANKING FUNCTIONS WITH DATE FILTERS (DB AGNOSTIC) ==============

def get_top_products(limit=20, start_date=None, end_date=None):
    """Get top selling products by category with revenue."""
    
    # In SQLite/Pandas approach: Fetch raw, Aggregate in Python
    query = """
    SELECT 
        COALESCE(t.product_category_name_english, p.product_category_name, 'Diğer') as product_category,
        oi.order_id,
        oi.price,
        o.order_purchase_timestamp
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    JOIN orders o ON oi.order_id = o.order_id
    LEFT JOIN product_category_name_translation t ON p.product_category_name = t.product_category_name
    """
    
    df = pd.read_sql(text(query), engine)
    
    if start_date and end_date:
        df['order_purchase_timestamp'] = pd.to_datetime(df['order_purchase_timestamp'])
        df = df[(df['order_purchase_timestamp'] >= pd.to_datetime(start_date)) & 
                (df['order_purchase_timestamp'] <= pd.to_datetime(end_date))]
    
    # Group By
    res = df.groupby('product_category').agg(
        order_count=('order_id', 'nunique'),
        total_sales=('price', 'sum')
    ).reset_index().sort_values('total_sales', ascending=False).head(limit)
    
    return res

def get_top_sellers(limit=20, start_date=None, end_date=None):
    """Get top sellers with performance metrics."""
    query = """
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
    """
    
    df = pd.read_sql(text(query), engine)
    
    if start_date and end_date:
        df['order_purchase_timestamp'] = pd.to_datetime(df['order_purchase_timestamp'])
        df = df[(df['order_purchase_timestamp'] >= pd.to_datetime(start_date)) & 
                (df['order_purchase_timestamp'] <= pd.to_datetime(end_date))]
        
    if df.empty:
        return pd.DataFrame()
        
    # Calculate On-Time per row
    df['order_delivered_customer_date'] = pd.to_datetime(df['order_delivered_customer_date'])
    df['order_estimated_delivery_date'] = pd.to_datetime(df['order_estimated_delivery_date'])
    df['is_on_time'] = df['order_delivered_customer_date'] <= df['order_estimated_delivery_date']
    
    # Group By
    res = df.groupby('seller_id').agg(
        order_count=('order_id', 'nunique'),
        total_revenue=('price', 'sum'),
        avg_rating=('review_score', 'mean'),
        on_time_count=('is_on_time', 'sum'),
        total_rows=('order_id', 'count')
    ).reset_index()
    
    # Correct On-Time Rate calculation
    res['on_time_rate'] = (res['on_time_count'] / res['total_rows']) * 100
    
    # Filter min 5 orders
    res = res[res['order_count'] >= 5]
    
    return res.sort_values('total_revenue', ascending=False).head(limit)

def get_category_performance(start_date=None, end_date=None):
    """Get category performance with revenue and ratings."""
    query = """
    SELECT 
        COALESCE(t.product_category_name_english, p.product_category_name, 'Diğer') as category,
        oi.price,
        r.review_score,
        oi.order_id,
        o.order_purchase_timestamp
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    JOIN orders o ON oi.order_id = o.order_id
    LEFT JOIN order_reviews r ON o.order_id = r.order_id
    LEFT JOIN product_category_name_translation t ON p.product_category_name = t.product_category_name
    WHERE o.order_status = 'delivered'
    """
    
    df = pd.read_sql(text(query), engine)
    
    if start_date and end_date:
        df['order_purchase_timestamp'] = pd.to_datetime(df['order_purchase_timestamp'])
        df = df[(df['order_purchase_timestamp'] >= pd.to_datetime(start_date)) & 
                (df['order_purchase_timestamp'] <= pd.to_datetime(end_date))]
    
    # Group
    res = df.groupby('category').agg(
        revenue=('price', 'sum'),
        avg_review=('review_score', 'mean'),
        order_count=('order_id', 'nunique')
    ).reset_index()
    
    res = res[res['revenue'] > 1000].sort_values('revenue', ascending=False).head(30)
    return res


def get_random_customer_id():
    try:
        return pd.read_sql('SELECT customer_unique_id FROM customers ORDER BY RANDOM() LIMIT 1', engine).iloc[0, 0]
    except:
        return '871766c5855e863f6eccc05f988b23'
