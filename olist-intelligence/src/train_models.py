import pandas as pd
import pickle
from pathlib import Path
from sqlalchemy import create_engine, text
from catboost import CatBoostRegressor, CatBoostClassifier
from sklearn.model_selection import train_test_split
from config import DATABASE_URL, MODELS_PATH

# 1. Setup
engine = create_engine(DATABASE_URL)
MODELS_PATH.mkdir(parents=True, exist_ok=True)

def train_logistics_model():
    print("📦 Eğitim Verisi Hazırlanıyor: Lojistik...")
    
    # Simple feature set for demonstration
    query = """
    SELECT 
        o.order_id,
        EXTRACT(EPOCH FROM (o.order_delivered_customer_date::timestamp - o.order_purchase_timestamp::timestamp))/86400 as target_days,
        oi.freight_value,
        oi.price,
        p.product_weight_g,
        p.product_description_lenght
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    JOIN products p ON oi.product_id = p.product_id
    WHERE o.order_status = 'delivered'
    AND o.order_delivered_customer_date IS NOT NULL
    LIMIT 10000
    """
    
    df = pd.read_sql(text(query), engine)
    df = df.dropna()
    
    X = df[['freight_value', 'price', 'product_weight_g', 'product_description_lenght']]
    y = df['target_days']
    
    print(f"📦 Model Eğitiliyor (Veri: {len(df)} satır)...")
    model = CatBoostRegressor(iterations=100, depth=6, learning_rate=0.1, verbose=0)
    model.fit(X, y)
    
    output_path = MODELS_PATH / "logistics_model.pkl"
    with open(output_path, "wb") as f:
        pickle.dump(model, f)
    
    print(f"✅ Lojistik Modeli Kaydedildi: {output_path}")

def train_churn_model():
    print("🔥 Eğitim Verisi Hazırlanıyor: Churn...")
    
    # Use segmentation results to train a classifier
    # Target: 1 if Cluster is High Risk (2 or 3), else 0
    query = """
    SELECT 
        "Recency",
        "Frequency",
        "Monetary",
        "Cluster"
    FROM customer_segments
    """
    
    try:
        df = pd.read_sql(text(query), engine)
    except Exception as e:
        print("⚠️ Customer Segments tablosu bulunamadı. Önce Notebook 4'ü çalıştırın veya mock data kullanın.")
        return

    # Create Binary Target: Risk vs Safe
    # Assuming Cluster 2 (At Risk) and 4 (Hibernating) are 'Churn'
    df['target'] = df['Cluster'].apply(lambda x: 1 if x in [2, 4] else 0)
    
    X = df[['Recency', 'Frequency', 'Monetary']]
    y = df['target']
    
    print(f"🔥 Model Eğitiliyor (Veri: {len(df)} satır)...")
    model = CatBoostClassifier(iterations=100, depth=4, learning_rate=0.1, verbose=0)
    model.fit(X, y)
    
    output_path = MODELS_PATH / "churn_model.pkl"
    with open(output_path, "wb") as f:
        pickle.dump(model, f)
        
    print(f"✅ Churn Modeli Kaydedildi: {output_path}")

from sklearn.decomposition import TruncatedSVD
import numpy as np
from scipy.sparse import csr_matrix

def train_recommender_model():
    print("🛍️ Eğitim Verisi Hazırlanıyor: Ürün Öneri Sistemi...")
    
    # Implicit Feedback: Purchase Count per User-Product
    query = """
    SELECT 
        o.customer_id, 
        oi.product_id,
        COUNT(*) as purchase_count
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.order_id
    GROUP BY 1, 2
    LIMIT 20000 
    """
    # Increased limit slightly but handled sparsely
    
    try:
        df = pd.read_sql(text(query), engine)
    except Exception as e:
        print(f"⚠️ Veri çekme hatası: {e}")
        return

    print(f"🛍️ Matris Oluşturuluyor ({len(df)} etkileşim)...")
    
    # Create User-Item Matrix
    user_ids = df['customer_id'].unique()
    product_ids = df['product_id'].unique()
    
    user_map = {id_: i for i, id_ in enumerate(user_ids)}
    product_map = {id_: i for i, id_ in enumerate(product_ids)}
    reverse_product_map = {i: id_ for id_, i in product_map.items()}
    
    df['user_idx'] = df['customer_id'].map(user_map)
    df['product_idx'] = df['product_id'].map(product_map)
    
    # SPARSE MATRIX CONSTRUCTION
    # data, (row_ind, col_ind)
    matrix_sparse = csr_matrix(
        (df['purchase_count'].values, (df['user_idx'].values, df['product_idx'].values)),
        shape=(len(user_ids), len(product_ids))
    )
    
    print(f"🛍️ Model (SVD) Eğitiliyor (Shape: {matrix_sparse.shape})...")
    
    # Reduce to 20 latent features
    svd = TruncatedSVD(n_components=min(20, len(product_ids)-1), random_state=42)
    matrix_reduced = svd.fit_transform(matrix_sparse)
    
    # We save everything needed for inference
    artifact = {
        "model": svd,
        "matrix_reduced": matrix_reduced, # User vectors
        "product_components": svd.components_, # Item vectors
        "user_map": user_map,
        "product_map": product_map,
        "reverse_product_map": reverse_product_map
    }
    
    output_path = MODELS_PATH / "recommender_model.pkl"
    with open(output_path, "wb") as f:
        pickle.dump(artifact, f)
        
    print(f"✅ Öneri Modeli Kaydedildi: {output_path}")

if __name__ == "__main__":
    train_logistics_model()
    train_churn_model()
    train_recommender_model()
