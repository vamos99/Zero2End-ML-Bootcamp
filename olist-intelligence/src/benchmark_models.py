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
from xgboost import XGBClassifier, XGBRegressor
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
    mlflow.set_experiment("Olist_Model_Wars_Optimized")
    MLFLOW_AVAILABLE = True
except Exception as e:
    print(f"⚠️ MLflow setup failed: {e}")
    print("⚠️ Continuing without MLflow logging...")

def get_logistics_data():
    """
    ENHANCED: Includes Geo features and Seller Rating.
    - Haversine distance, same_state
    - seller_avg_rating from 99K reviews (new)
    """
    query = """
    WITH seller_geo AS (
        SELECT DISTINCT ON (seller_zip_code_prefix)
            seller_zip_code_prefix,
            AVG(geolocation_lat) as seller_lat,
            AVG(geolocation_lng) as seller_lng
        FROM sellers s
        LEFT JOIN geolocation g ON s.seller_zip_code_prefix = g.geolocation_zip_code_prefix
        GROUP BY seller_zip_code_prefix
    ),
    customer_geo AS (
        SELECT DISTINCT ON (customer_zip_code_prefix)
            customer_zip_code_prefix,
            AVG(geolocation_lat) as cust_lat,
            AVG(geolocation_lng) as cust_lng
        FROM customers c
        LEFT JOIN geolocation g ON c.customer_zip_code_prefix = g.geolocation_zip_code_prefix
        GROUP BY customer_zip_code_prefix
    ),
    seller_ratings AS (
        SELECT 
            oi2.seller_id,
            AVG(r.review_score) as seller_avg_rating,
            COUNT(*) as review_count
        FROM order_items oi2
        JOIN orders o2 ON oi2.order_id = o2.order_id
        JOIN order_reviews r ON o2.order_id = r.order_id
        GROUP BY oi2.seller_id
        HAVING COUNT(*) >= 5
    )
    SELECT 
        EXTRACT(EPOCH FROM (o.order_delivered_customer_date::timestamp - o.order_purchase_timestamp::timestamp))/86400 as target_days,
        oi.freight_value,
        oi.price,
        p.product_weight_g,
        p.product_description_lenght,
        sg.seller_lat,
        sg.seller_lng,
        cg.cust_lat,
        cg.cust_lng,
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
    df = pd.read_sql(text(query), engine).dropna()
    
    # Calculate Haversine distance
    from src.features import haversine_distance
    df['distance_km'] = haversine_distance(
        df['seller_lat'], df['seller_lng'],
        df['cust_lat'], df['cust_lng']
    )
    
    # Features now include seller rating
    feature_cols = ['freight_value', 'price', 'product_weight_g', 'product_description_lenght', 
                    'distance_km', 'same_state', 'seller_avg_rating']
    
    print(f"Logistics Data: {len(df)} orders, Avg Distance: {df['distance_km'].mean():.1f} km, Avg Seller Rating: {df['seller_avg_rating'].mean():.2f}")
    
    return df[feature_cols], df['target_days']

def get_churn_data():
    """
    FIXED: Real Time-Based Churn Definition.
    Churn = Customer who hasn't ordered in the last 90 days (relative to dataset's max date).
    This avoids data leakage from cluster-based targets.
    """
    query = """
    WITH customer_orders AS (
        SELECT 
            c.customer_unique_id,
            MAX(o.order_purchase_timestamp::timestamp) as last_order_date,
            COUNT(*) as order_count,
            SUM(oi.price) as total_spent
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        JOIN order_items oi ON o.order_id = oi.order_id
        WHERE o.order_status = 'delivered'
        GROUP BY c.customer_unique_id
    ),
    dataset_bounds AS (
        SELECT MAX(last_order_date) as max_date FROM customer_orders
    )
    SELECT 
        co.customer_unique_id,
        EXTRACT(EPOCH FROM (db.max_date::timestamp - co.last_order_date::timestamp))/86400 as days_since_last_order,
        co.order_count as frequency,
        co.total_spent as monetary,
        CASE 
            WHEN EXTRACT(EPOCH FROM (db.max_date::timestamp - co.last_order_date::timestamp))/86400 > 90 THEN 1 
            ELSE 0 
        END as is_churned
    FROM customer_orders co
    CROSS JOIN dataset_bounds db
    LIMIT 50000
    """
    try:
        df = pd.read_sql(text(query), engine).dropna()
        print(f"📊 Churn Data: {len(df)} customers, Churn Rate: {df['is_churned'].mean()*100:.1f}%")
        X = df[['days_since_last_order', 'frequency', 'monetary']]
        y = df['is_churned']
        return X, y
    except Exception as e:
        print(f"⚠️ Churn data error: {e}")
        return None, None

def benchmark_logistics():
    print("\n📦 --- Logistics Model Wars (Optimized) ---")
    X, y = get_logistics_data()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    models = {
        "LinearRegression": LinearRegression(),
        "RandomForest": RandomForestRegressor(n_estimators=50, max_depth=10, random_state=42),
        "CatBoost": CatBoostRegressor(iterations=100, depth=6, verbose=0, random_state=42)
    }
    
    results = {}
    for name, model in models.items():
        start = time.time()
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        rmse = np.sqrt(mean_squared_error(y_test, preds))
        duration = time.time() - start
        
        results[name] = {"RMSE": rmse, "Time": duration}
        print(f"👉 {name}: RMSE={rmse:.4f} (Time: {duration:.2f}s)")
        
        # Log to MLflow
        if MLFLOW_AVAILABLE:
            try:
                with mlflow.start_run(run_name=f"Logistics_{name}"):
                    mlflow.log_param("model", name)
                    mlflow.log_metric("rmse", rmse)
                    mlflow.log_metric("training_time", duration)
            except Exception as e:
                print(f"⚠️ MLflow logging failed: {e}")
            
    best_model_name = min(results, key=lambda k: results[k]["RMSE"])
    print(f"🏆 Winner: {best_model_name}")
    
    # Rigorous Optimization with Optuna for the Winner
    if best_model_name == "CatBoost":
        print("🔧 Optimizing CatBoost with Optuna (20 Trials)...")
        def objective(trial):
            params = {
                "iterations": trial.suggest_int("iterations", 100, 1000),
                "depth": trial.suggest_int("depth", 4, 10),
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3),
                "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1e-8, 100.0, log=True),
                "verbose": 0,
                "random_state": 42
            }
            model = CatBoostRegressor(**params)
            score = -cross_val_score(model, X_train, y_train, cv=3, scoring="neg_root_mean_squared_error").mean()
            return score
            
        study = optuna.create_study(direction="minimize")
        study.optimize(objective, n_trials=20) 
        print(f"✨ Best Params: {study.best_params}")
        
        final_model = CatBoostRegressor(**study.best_params, verbose=0)
        final_model.fit(X, y)
        
    elif best_model_name == "RandomForest":
        print("🔧 Optimizing RandomForest with Optuna (20 Trials)...")
        def objective(trial):
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 50, 200),
                "max_depth": trial.suggest_int("max_depth", 5, 20),
                "min_samples_split": trial.suggest_int("min_samples_split", 2, 10),
                "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 5),
                "random_state": 42
            }
            model = RandomForestRegressor(**params)
            score = -cross_val_score(model, X_train, y_train, cv=3, scoring="neg_root_mean_squared_error").mean()
            return score
            
        study = optuna.create_study(direction="minimize")
        study.optimize(objective, n_trials=20)
        print(f"✨ Best Params: {study.best_params}")
        
        final_model = RandomForestRegressor(**study.best_params)
        final_model.fit(X, y)
        
    else:
        # Default fallback
        final_model = models[best_model_name]
        final_model.fit(X, y)

    # Save Optimized Model
    with open(MODELS_PATH / "logistics_model.pkl", "wb") as f:
        pickle.dump(final_model, f)
    print(f"✅ Optimized Model ({best_model_name}) Saved")

def benchmark_churn():
    print("\n🔥 --- Churn Model Wars (Optimized) ---")
    X, y = get_churn_data()
    if X is None:
        print("Skipping Churn (No Data)")
        return
        
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    models = {
        "LogisticRegression": LogisticRegression(),
        "RandomForest": RandomForestClassifier(n_estimators=50, max_depth=10, random_state=42),
        "CatBoost": CatBoostClassifier(iterations=100, depth=6, verbose=0, random_state=42),
        "XGBoost": XGBClassifier(n_estimators=50, max_depth=6, eval_metric='logloss', random_state=42)
    }
    
    results = {}
    for name, model in models.items():
        start = time.time()
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        prob = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else preds
        
        acc = accuracy_score(y_test, preds)
        auc = roc_auc_score(y_test, prob)
        duration = time.time() - start
        
        results[name] = {"AUC": auc, "ACC": acc}
        print(f"👉 {name}: AUC={auc:.4f}, ACC={acc:.4f}")
        
        if MLFLOW_AVAILABLE:
            try:
                with mlflow.start_run(run_name=f"Churn_{name}"):
                    mlflow.log_param("model", name)
                    mlflow.log_metric("auc", auc)
                    mlflow.log_metric("accuracy", acc)
            except Exception as e:
                print(f"⚠️ MLflow logging failed: {e}")

    best_model_name = max(results, key=lambda k: results[k]["AUC"])
    print(f"🏆 Winner: {best_model_name}")
    
    # Save winner
    model = models[best_model_name]
    model.fit(X, y) # Retrain on full data
    with open(MODELS_PATH / "churn_model.pkl", "wb") as f:
        pickle.dump(model, f)
    print(f"✅ Best Model ({best_model_name}) Saved!")

if __name__ == "__main__":
    benchmark_logistics()
    benchmark_churn()
