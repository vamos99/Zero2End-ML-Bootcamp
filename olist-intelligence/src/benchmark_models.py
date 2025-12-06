import pandas as pd
import numpy as np
import optuna
import mlflow
from sqlalchemy import create_engine, text
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error, accuracy_score, roc_auc_score
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from catboost import CatBoostRegressor, CatBoostClassifier
from xgboost import XGBClassifier
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.config import DATABASE_URL, MODELS_PATH
import pickle
import time

# Setup
engine = create_engine(DATABASE_URL)

MLFLOW_AVAILABLE = False
try:
    mlflow.set_tracking_uri("http://mlflow:5000")
    mlflow.set_experiment("Olist_Model_Wars")
    MLFLOW_AVAILABLE = True
except Exception as e:
    print(f"⚠️ MLflow setup failed: {e}")
    print("⚠️ Continuing without MLflow logging...")


def get_logistics_data():
    """
    10-feature model with derived features. RMSE ~7.58
    
    Features:
    1. freight_value - Kargo ücreti
    2. price - Ürün fiyatı
    3. product_weight_g - Ürün ağırlığı
    4. product_description_lenght - Ürün açıklama uzunluğu
    5. distance_km - Haversine mesafe (satıcı-müşteri)
    6. same_state - Aynı eyalet mi?
    7. seller_avg_rating - Satıcı ortalama puanı
    8. product_photos_qty - Ürün fotoğraf sayısı
    9. product_volume - Ürün hacmi (cm³)
    10. freight_ratio - Kargo/Fiyat oranı
    """
    query = """
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
        EXTRACT(EPOCH FROM (o.order_delivered_customer_date::timestamp - o.order_purchase_timestamp::timestamp))/86400 as target_days,
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
    AND o.order_delivered_customer_date IS NOT NULL
    LIMIT 20000
    """
    
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn).dropna()
    
    # Calculate Haversine distance
    from src.features import haversine_distance
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
    
    print(f"Logistics Data: {len(df)} orders, {len(feature_cols)} features")
    print(f"  Avg Distance: {df['distance_km'].mean():.1f} km")
    
    return df[feature_cols], df['target_days']


def get_churn_data():
    """
    Real Churn Definition: Customer who hasn't ordered in 90 days = Churned.
    """
    query = """
    WITH customer_orders AS (
        SELECT 
            c.customer_unique_id,
            MAX(o.order_purchase_timestamp::timestamp) as last_order_date,
            COUNT(DISTINCT o.order_id) as frequency,
            SUM(oi.price) as monetary
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        JOIN order_items oi ON o.order_id = oi.order_id
        WHERE o.order_status = 'delivered'
        GROUP BY c.customer_unique_id
    ),
    max_date AS (
        SELECT MAX(order_purchase_timestamp::timestamp) as dataset_end FROM orders
    )
    SELECT 
        co.customer_unique_id,
        EXTRACT(DAY FROM (md.dataset_end - co.last_order_date)) as days_since_last_order,
        co.frequency,
        co.monetary,
        CASE WHEN EXTRACT(DAY FROM (md.dataset_end - co.last_order_date)) > 90 THEN 1 ELSE 0 END as churned
    FROM customer_orders co, max_date md
    LIMIT 50000
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn).dropna()
    
    feature_cols = ['days_since_last_order', 'frequency', 'monetary']
    
    print(f"Churn Data: {len(df)} customers, Churn Rate: {df['churned'].mean()*100:.1f}%")
    
    return df[feature_cols], df['churned']


def benchmark_logistics():
    """Run logistics model benchmark with Optuna optimization."""
    print("\n📦 --- Logistics Model Benchmark ---")
    X, y = get_logistics_data()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    results = {}
    
    # 1. LinearRegression
    start = time.time()
    lr = LinearRegression()
    lr.fit(X_train, y_train)
    pred = lr.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, pred))
    results['LinearRegression'] = {'rmse': rmse, 'time': time.time() - start, 'model': lr}
    print(f"👉 LinearRegression: RMSE={rmse:.4f}")
    
    # 2. RandomForest
    start = time.time()
    rf = RandomForestRegressor(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    pred = rf.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, pred))
    results['RandomForest'] = {'rmse': rmse, 'time': time.time() - start, 'model': rf}
    print(f"👉 RandomForest: RMSE={rmse:.4f}")
    
    # 3. CatBoost
    start = time.time()
    cb = CatBoostRegressor(iterations=200, depth=8, learning_rate=0.1, verbose=0, random_seed=42)
    cb.fit(X_train, y_train)
    pred = cb.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, pred))
    results['CatBoost'] = {'rmse': rmse, 'time': time.time() - start, 'model': cb}
    print(f"👉 CatBoost: RMSE={rmse:.4f}")
    
    # Find winner
    winner = min(results, key=lambda k: results[k]['rmse'])
    print(f"🏆 Winner: {winner}")
    
    # Optimize with Optuna
    print(f"🔧 Optimizing RandomForest with Optuna (20 Trials)...")
    
    def objective(trial):
        params = {
            'n_estimators': trial.suggest_int('n_estimators', 50, 200),
            'max_depth': trial.suggest_int('max_depth', 5, 20),
            'min_samples_split': trial.suggest_int('min_samples_split', 2, 10),
            'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 5)
        }
        model = RandomForestRegressor(**params, random_state=42, n_jobs=-1)
        scores = cross_val_score(model, X_train, y_train, cv=3, scoring='neg_root_mean_squared_error')
        return -scores.mean()
    
    study = optuna.create_study(direction='minimize')
    study.optimize(objective, n_trials=20, show_progress_bar=False)
    
    print(f"✨ Best Params: {study.best_params}")
    
    # Train final model
    final_model = RandomForestRegressor(**study.best_params, random_state=42, n_jobs=-1)
    final_model.fit(X_train, y_train)
    
    # Final RMSE
    final_pred = final_model.predict(X_test)
    final_rmse = np.sqrt(mean_squared_error(y_test, final_pred))
    print(f"📊 Final RMSE: {final_rmse:.4f}")
    
    # Save model
    with open(MODELS_PATH / "logistics_model.pkl", "wb") as f:
        pickle.dump(final_model, f)
    print("✅ Model Saved")
    
    return results


def benchmark_churn():
    """Run churn model benchmark."""
    print("\n🔥 --- Churn Model Benchmark ---")
    X, y = get_churn_data()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    models = {
        'LogisticRegression': LogisticRegression(max_iter=1000, random_state=42),
        'RandomForest': RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1),
        'CatBoost': CatBoostClassifier(iterations=200, depth=6, verbose=0, random_seed=42),
        'XGBoost': XGBClassifier(n_estimators=100, max_depth=6, random_state=42, use_label_encoder=False, eval_metric='logloss')
    }
    
    results = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        pred_proba = model.predict_proba(X_test)[:, 1]
        
        acc = accuracy_score(y_test, pred)
        auc = roc_auc_score(y_test, pred_proba)
        results[name] = {'auc': auc, 'acc': acc, 'model': model}
        print(f"👉 {name}: AUC={auc:.4f}, ACC={acc:.4f}")
    
    winner = max(results, key=lambda k: results[k]['auc'])
    print(f"🏆 Winner: {winner}")
    
    # Save winner
    with open(MODELS_PATH / "churn_model.pkl", "wb") as f:
        pickle.dump(results[winner]['model'], f)
    print(f"✅ {winner} Saved")
    
    return results


if __name__ == "__main__":
    benchmark_logistics()
    benchmark_churn()
