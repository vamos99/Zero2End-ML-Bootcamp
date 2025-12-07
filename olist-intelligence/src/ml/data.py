import pandas as pd
from sqlalchemy import text, create_engine
from src.config import DATABASE_URL
from src.ml.features import haversine_distance

def get_db_engine():
    return create_engine(DATABASE_URL)

def get_logistics_data(limit=None):
    """
    Fetches data for logistics model (delivery time prediction).
    Returns X (features DataFrame) and y (target Series).
    Logic moved to Pandas for SQLite compatibility.
    """
    limit_clause = f"LIMIT {limit}" if limit else ""
    
    # Raw data query (DB Agnostic)
    query = f"""
    SELECT 
        o.order_purchase_timestamp,
        o.order_delivered_customer_date,
        oi.freight_value,
        oi.price,
        p.product_weight_g,
        p.product_description_lenght,
        p.product_photos_qty,
        p.product_length_cm,
        p.product_height_cm,
        p.product_width_cm,
        s.seller_zip_code_prefix,
        s.seller_state,
        s.seller_id,
        c.customer_zip_code_prefix,
        c.customer_state
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    JOIN products p ON oi.product_id = p.product_id
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN sellers s ON oi.seller_id = s.seller_id
    WHERE o.order_status = 'delivered'
    AND o.order_delivered_customer_date IS NOT NULL
    {limit_clause}
    """
    
    engine = get_db_engine()
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn).dropna()

    # Load aux tables for merging (Seller Ratings & Geolocation)
    # We do this separately to avoid complex joins in SQLite/Polars
    with engine.connect() as conn:
        reviews = pd.read_sql(text("SELECT order_id, review_score FROM order_reviews"), conn)
        # Note: We need order_items to link seller -> order -> review, but we can approximate
        # For simplicity in this demo refactor, we re-query seller ratings if needed or calculate here.
        
        # Better approach: Calculate seller ratings from full order_items + reviews dump
        # But for performance let's keep it simple. If table is huge, this is slow.
        # SQLite doesn't support complex lateral joins easily.
        
        # Let's fetch pre-calculated geolocation if possible, or calculate on fly.
        # For this refactor, we will load full geolocation table? It is 1M rows. Too big.
        # We will use a simplified approach: Group inputs by zip code in Python? No.
        
        # Compromise: Keep the JOINs simple in SQL
        pass

    # REVISIT: The original query used subqueries for Geolocation. 
    # SQLite SUPPORTS subqueries. The problem was EXTRACT and ::timestamp.
    # So we can keep the structure but fix the DATE math.
    
    query = f"""
    WITH seller_geo AS (
        SELECT seller_zip_code_prefix, AVG(geolocation_lat) as lat, AVG(geolocation_lng) as lng
        FROM sellers s
        LEFT JOIN geolocation g ON s.seller_zip_code_prefix = g.geolocation_zip_code_prefix
        GROUP BY seller_zip_code_prefix
    ),
    customer_geo AS (
        SELECT customer_zip_code_prefix, AVG(geolocation_lat) as lat, AVG(geolocation_lng) as lng
        FROM customers c
        LEFT JOIN geolocation g ON c.customer_zip_code_prefix = g.geolocation_zip_code_prefix
        GROUP BY customer_zip_code_prefix
    ),
    seller_ratings AS (
        SELECT oi2.seller_id, AVG(r.review_score) as seller_avg_rating
        FROM order_items oi2
        JOIN order_reviews r ON oi2.order_id = r.order_id
        GROUP BY oi2.seller_id
        HAVING COUNT(*) >= 5
    )
    SELECT 
        o.order_purchase_timestamp,
        o.order_delivered_customer_date,
        oi.freight_value,
        oi.price,
        p.product_weight_g,
        p.product_description_lenght,
        COALESCE(p.product_photos_qty, 1) as product_photos_qty,
        COALESCE(p.product_length_cm * p.product_height_cm * p.product_width_cm, 5000) as product_volume,
        sg.lat as seller_lat,
        sg.lng as seller_lng,
        cg.lat as cust_lat,
        cg.lng as cust_lng,
        CASE WHEN s.seller_state = c.customer_state THEN 1 ELSE 0 END as same_state,
        COALESCE(sr.seller_avg_rating, 4.0) as seller_avg_rating
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    JOIN products p ON oi.product_id = p.product_id
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN sellers s ON oi.seller_id = s.seller_id
    LEFT JOIN seller_geo sg ON s.seller_zip_code_prefix = sg.seller_zip_code_prefix
    LEFT JOIN customer_geo cg ON c.customer_zip_code_prefix = cg.customer_zip_code_prefix
    LEFT JOIN seller_ratings sr ON s.seller_id = sr.seller_id
    WHERE o.order_status = 'delivered'
    {limit_clause}
    """
    
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn).dropna()
        
    # --- Python Logic for Date Calculation (DB Agnostic) ---
    df['order_purchase_timestamp'] = pd.to_datetime(df['order_purchase_timestamp'])
    df['order_delivered_customer_date'] = pd.to_datetime(df['order_delivered_customer_date'])
    
    # Target Days calculation
    df['target_days'] = (df['order_delivered_customer_date'] - df['order_purchase_timestamp']).dt.total_seconds() / 86400
    
    # Filter valid dates (delivered after purchase)
    df = df[df['target_days'] > 0]
    
    # Calculate Haversine distance
    df['distance_km'] = haversine_distance(
        df['seller_lat'], df['seller_lng'],
        df['cust_lat'], df['cust_lng']
    )
    
    # Derived feature: freight_ratio
    df['freight_ratio'] = df['freight_value'] / df['price'].replace(0, 1)
    
    # 10 Features
    feature_cols = [
        'freight_value',           # 1
        'price',                   # 2
        'product_weight_g',        # 3
        'product_description_lenght',  # 4
        'distance_km',             # 5
        'same_state',              # 6
        'seller_avg_rating',       # 7
        'product_photos_qty',      # 8
        'product_volume',          # 9
        'freight_ratio'            # 10
    ]
    
    return df[feature_cols], df['target_days']

def get_churn_data(limit=None):
    """
    Fetches data for churn model.
    Returns X (features DataFrame) and y (target Series).
    Logic moved to Pandas for SQLite compatibility.
    """
    limit_clause = f"LIMIT {limit}" if limit else ""
    
    # 1. Fetch Customer Orders
    query_orders = f"""
    SELECT 
        c.customer_unique_id,
        o.order_purchase_timestamp,
        o.order_id,
        oi.price
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
    {limit_clause}
    """
    
    # 2. Fetch Dataset End Date (Global Max)
    query_max_date = "SELECT MAX(order_purchase_timestamp) FROM orders"
    
    engine = get_db_engine()
    with engine.connect() as conn:
        df = pd.read_sql(text(query_orders), conn)
        max_date_str = pd.read_sql(text(query_max_date), conn).iloc[0, 0]
        
    # --- Python Logic ---
    df['order_purchase_timestamp'] = pd.to_datetime(df['order_purchase_timestamp'])
    dataset_end = pd.to_datetime(max_date_str)
    
    # Aggregation
    customer_group = df.groupby('customer_unique_id').agg(
        last_order_date=('order_purchase_timestamp', 'max'),
        frequency=('order_id', 'nunique'),
        monetary=('price', 'sum')
    ).reset_index()
    
    # Churn Calculation
    customer_group['days_since_last_order'] = (dataset_end - customer_group['last_order_date']).dt.days
    customer_group['churned'] = (customer_group['days_since_last_order'] > 90).astype(int)
    
    feature_cols = ['days_since_last_order', 'frequency', 'monetary']
    
    return customer_group[feature_cols], customer_group['churned']

def get_recommender_data(limit=None):
    """
    Fetches user-item interaction data for recommender system.
    Returns DataFrame with [customer_id, product_id, purchase_count].
    """
    limit_clause = f"LIMIT {limit}" if limit else ""
    
    query = f"""
    SELECT 
        c.customer_unique_id as customer_id, 
        oi.product_id,
        COUNT(*) as purchase_count
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.order_id
    JOIN customers c ON o.customer_id = c.customer_id
    GROUP BY 1, 2
    {limit_clause}
    """
    
    engine = get_db_engine()
    try:
        data = pd.read_sql(text(query), engine)
        return data
    except Exception as e:
        print(f"⚠️ Veri çekme hatası: {e}")
        return pd.DataFrame()
