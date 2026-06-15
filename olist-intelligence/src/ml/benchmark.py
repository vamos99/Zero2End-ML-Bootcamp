import numpy as np
import optuna
import time
import pickle
from sklearn.model_selection import TimeSeriesSplit, train_test_split, cross_val_score
from sklearn.metrics import balanced_accuracy_score, mean_squared_error, roc_auc_score
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from catboost import CatBoostRegressor, CatBoostClassifier
from xgboost import XGBClassifier
from src.config import MODELS_PATH
from src.ml.data import get_logistics_data, get_churn_data
from src.ml.evaluation import has_usable_class_balance, temporal_train_test_split

def benchmark_logistics():
    """Run logistics model benchmark with Optuna optimization."""
    print("\n📦 --- Logistics Model Benchmark ---")
    X, y, timestamps = get_logistics_data(limit=20000, include_timestamps=True)
    
    print(f"Logistics Data: {len(X)} orders, {X.shape[1]} features")
    
    X_train, X_test, y_train, y_test = temporal_train_test_split(
        X, y, timestamps, test_size=0.2
    )
    
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
        scores = cross_val_score(
            model,
            X_train,
            y_train,
            cv=TimeSeriesSplit(n_splits=3),
            scoring='neg_root_mean_squared_error',
        )
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
    X, y = get_churn_data(limit=50000)
    
    print(f"Churn Data: {len(X)} customers, Churn Rate: {y.mean()*100:.1f}%")

    if not has_usable_class_balance(y):
        print(f"⚠️ Benchmark skipped: class balance is not evaluation-ready ({y.value_counts().sort_index().to_dict()}).")
        return {}

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    models = {
        'LogisticRegression': LogisticRegression(max_iter=1000, random_state=42),
        'RandomForest': RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1),
        'CatBoost': CatBoostClassifier(iterations=200, depth=6, verbose=0, random_seed=42, auto_class_weights='Balanced'),
        'XGBoost': XGBClassifier(n_estimators=100, max_depth=6, random_state=42, eval_metric='logloss')
    }
    
    results = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        pred_proba = model.predict_proba(X_test)[:, 1]
        
        balanced_acc = balanced_accuracy_score(y_test, pred)
        auc = roc_auc_score(y_test, pred_proba)
        results[name] = {'auc': auc, 'balanced_accuracy': balanced_acc, 'model': model}
        print(f"👉 {name}: AUC={auc:.4f}, Balanced ACC={balanced_acc:.4f}")
    
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
