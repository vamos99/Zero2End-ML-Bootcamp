import argparse
import numpy as np
import time
import pickle
from sklearn.base import clone
from sklearn.model_selection import TimeSeriesSplit, train_test_split, cross_val_score
from sklearn.metrics import (
    balanced_accuracy_score,
    mean_absolute_error,
    mean_squared_error,
    roc_auc_score,
)
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from catboost import CatBoostRegressor, CatBoostClassifier
from src.config import MODELS_PATH
from src.ml.data import get_logistics_data, get_churn_data
from src.ml.evaluation import expanding_temporal_splits, has_usable_class_balance, temporal_train_test_split

try:
    import optuna
except ImportError:
    optuna = None

try:
    from xgboost import XGBClassifier
except ImportError:
    XGBClassifier = None


def _rmse(actual, predicted):
    return float(np.sqrt(mean_squared_error(actual, predicted)))


def _mae(actual, predicted):
    return float(mean_absolute_error(actual, predicted))


def _improvement_pct(baseline_error, model_error):
    return float((baseline_error - model_error) / baseline_error * 100)


def _maybe_save_pickle(model, path, save_artifacts):
    if not save_artifacts:
        print(f"Artifact save skipped: {path}")
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(model, f)
    print(f"✅ Model saved: {path}")
    return True


def benchmark_logistics(limit=20000, optimize=True, save_artifacts=False):
    """Run logistics model benchmark without writing model artifacts by default."""
    print("\n📦 --- Logistics Model Benchmark ---")
    X, y, timestamps, estimated_days = get_logistics_data(
        limit=limit,
        include_timestamps=True,
        include_estimates=True,
    )
    
    print(f"Logistics Data: {len(X)} orders, {X.shape[1]} features")
    
    target_frame = y.to_frame(name="actual_days")
    target_frame["estimated_days"] = estimated_days
    X_train, X_test, y_train_frame, y_test_frame = temporal_train_test_split(
        X, target_frame, timestamps, test_size=0.2
    )
    y_train = y_train_frame["actual_days"]
    y_test = y_test_frame["actual_days"]
    source_estimate = y_test_frame["estimated_days"]

    train_mean_prediction = np.full(len(y_test), float(y_train.mean()))
    train_mean_rmse = _rmse(y_test, train_mean_prediction)
    train_mean_mae = _mae(y_test, train_mean_prediction)
    source_estimate_rmse = _rmse(y_test, source_estimate)
    source_estimate_mae = _mae(y_test, source_estimate)

    print(
        "Baselines: "
        f"train-mean RMSE={train_mean_rmse:.4f}, MAE={train_mean_mae:.4f}; "
        f"source-estimate RMSE={source_estimate_rmse:.4f}, MAE={source_estimate_mae:.4f}"
    )
    
    results = {}
    
    # 1. LinearRegression
    start = time.time()
    lr = LinearRegression()
    lr.fit(X_train, y_train)
    pred = lr.predict(X_test)
    rmse = _rmse(y_test, pred)
    mae = _mae(y_test, pred)
    results['LinearRegression'] = {
        'rmse': rmse,
        'mae': mae,
        'time': time.time() - start,
        'model': lr,
    }
    print(f"👉 LinearRegression: RMSE={rmse:.4f}, MAE={mae:.4f}")
    
    # 2. RandomForest
    start = time.time()
    rf = RandomForestRegressor(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    pred = rf.predict(X_test)
    rmse = _rmse(y_test, pred)
    mae = _mae(y_test, pred)
    results['RandomForest'] = {
        'rmse': rmse,
        'mae': mae,
        'time': time.time() - start,
        'model': rf,
    }
    print(f"👉 RandomForest: RMSE={rmse:.4f}, MAE={mae:.4f}")
    
    # 3. CatBoost
    start = time.time()
    cb = CatBoostRegressor(iterations=200, depth=8, learning_rate=0.1, verbose=0, random_seed=42)
    cb.fit(X_train, y_train)
    pred = cb.predict(X_test)
    rmse = _rmse(y_test, pred)
    mae = _mae(y_test, pred)
    results['CatBoost'] = {
        'rmse': rmse,
        'mae': mae,
        'time': time.time() - start,
        'model': cb,
    }
    print(f"👉 CatBoost: RMSE={rmse:.4f}, MAE={mae:.4f}")
    
    # Find winner
    winner = min(results, key=lambda k: results[k]['rmse'])
    print(f"🏆 Winner: {winner}")
    results["baselines"] = {
        "train_mean_rmse": train_mean_rmse,
        "train_mean_mae": train_mean_mae,
        "source_estimate_rmse": source_estimate_rmse,
        "source_estimate_mae": source_estimate_mae,
    }
    results[winner]["rmse_improvement_vs_train_mean_pct"] = _improvement_pct(
        train_mean_rmse,
        results[winner]["rmse"],
    )
    results[winner]["mae_improvement_vs_train_mean_pct"] = _improvement_pct(
        train_mean_mae,
        results[winner]["mae"],
    )
    results[winner]["rmse_improvement_vs_source_estimate_pct"] = _improvement_pct(
        source_estimate_rmse,
        results[winner]["rmse"],
    )
    results[winner]["mae_improvement_vs_source_estimate_pct"] = _improvement_pct(
        source_estimate_mae,
        results[winner]["mae"],
    )

    cutoff_rmses = []
    for split in expanding_temporal_splits(X, y, timestamps, n_splits=3, test_size=0.1):
        split_X_train, split_X_test, split_y_train, split_y_test = split
        cutoff_model = clone(results[winner]["model"])
        cutoff_model.fit(split_X_train, split_y_train)
        cutoff_prediction = cutoff_model.predict(split_X_test)
        cutoff_rmses.append(_rmse(split_y_test, cutoff_prediction))
    results[winner]["multi_cutoff_rmse"] = cutoff_rmses
    print(f"📊 Multi-cutoff RMSE: {[round(value, 4) for value in cutoff_rmses]}")

    if not optimize or optuna is None:
        if optimize and optuna is None:
            print("⚠️ Optuna is not installed; skipping optimization phase.")
        _maybe_save_pickle(results[winner]["model"], MODELS_PATH / "logistics_model.pkl", save_artifacts)
        return results
    
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
    final_rmse = _rmse(y_test, final_pred)
    final_mae = _mae(y_test, final_pred)
    results["OptimizedRandomForest"] = {
        "rmse": final_rmse,
        "mae": final_mae,
        "best_params": study.best_params,
        "rmse_improvement_vs_train_mean_pct": _improvement_pct(
            train_mean_rmse,
            final_rmse,
        ),
        "mae_improvement_vs_train_mean_pct": _improvement_pct(
            train_mean_mae,
            final_mae,
        ),
        "rmse_improvement_vs_source_estimate_pct": _improvement_pct(
            source_estimate_rmse,
            final_rmse,
        ),
        "mae_improvement_vs_source_estimate_pct": _improvement_pct(
            source_estimate_mae,
            final_mae,
        ),
    }
    print(f"📊 Final RMSE: {final_rmse:.4f}, MAE: {final_mae:.4f}")
    
    _maybe_save_pickle(final_model, MODELS_PATH / "logistics_model.pkl", save_artifacts)
    
    return results


def benchmark_churn(limit=50000, save_artifacts=False):
    """Run churn model benchmark without writing model artifacts by default."""
    print("\n🔥 --- Churn Model Benchmark ---")
    X, y = get_churn_data(limit=limit)
    
    print(f"Churn Data: {len(X)} customers, Churn Rate: {y.mean()*100:.1f}%")

    if not has_usable_class_balance(y):
        print(f"⚠️ Benchmark skipped: class balance is not evaluation-ready ({y.value_counts().sort_index().to_dict()}).")
        return {}

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    models = {
        'LogisticRegression': LogisticRegression(max_iter=1000, random_state=42),
        'RandomForest': RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1,
        ),
        'CatBoost': CatBoostClassifier(
            iterations=200,
            depth=6,
            verbose=0,
            random_seed=42,
            auto_class_weights='Balanced',
        ),
    }
    if XGBClassifier is not None:
        models['XGBoost'] = XGBClassifier(
            n_estimators=100,
            max_depth=6,
            random_state=42,
            eval_metric='logloss',
        )
    
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
    
    _maybe_save_pickle(results[winner]['model'], MODELS_PATH / "churn_model.pkl", save_artifacts)
    
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run local Olist model benchmarks.")
    parser.add_argument(
        "--save-artifacts",
        action="store_true",
        help="Write winning benchmark models to models/.",
    )
    parser.add_argument("--skip-optuna", action="store_true", help="Skip the Optuna optimization phase.")
    parser.add_argument("--logistics-limit", type=int, default=20000)
    parser.add_argument("--churn-limit", type=int, default=50000)
    args = parser.parse_args()

    benchmark_logistics(
        limit=args.logistics_limit,
        optimize=not args.skip_optuna,
        save_artifacts=args.save_artifacts,
    )
    benchmark_churn(limit=args.churn_limit, save_artifacts=args.save_artifacts)
