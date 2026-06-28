"""Compute measured Olist benchmark results without writing model artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from catboost import CatBoostRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.ml.data import get_churn_data, get_logistics_data, get_recommender_data  # noqa: E402
from src.ml.evaluation import has_usable_class_balance, temporal_train_test_split  # noqa: E402
from src.ml.recommender import evaluate_leave_one_out  # noqa: E402


def _rmse(actual, predicted) -> float:
    return float(np.sqrt(mean_squared_error(actual, predicted)))


def delivery_benchmark(limit: int = 50_000) -> dict[str, Any]:
    """Return temporal holdout metrics and naive-baseline comparison."""
    features, target, timestamps = get_logistics_data(limit=limit, include_timestamps=True)
    x_train, x_test, y_train, y_test = temporal_train_test_split(
        features,
        target,
        timestamps,
        test_size=0.2,
    )

    model = CatBoostRegressor(
        iterations=200,
        depth=8,
        learning_rate=0.1,
        verbose=0,
        random_seed=42,
    )
    model.fit(x_train, y_train)
    prediction = model.predict(x_test)
    baseline_prediction = np.full(len(y_test), float(y_train.mean()))

    model_rmse = _rmse(y_test, prediction)
    baseline_rmse = _rmse(y_test, baseline_prediction)
    model_mae = float(mean_absolute_error(y_test, prediction))
    baseline_mae = float(mean_absolute_error(y_test, baseline_prediction))
    actual_mean = float(np.mean(y_test))
    prediction_mean = float(np.mean(prediction))

    return {
        "rows": int(len(features)),
        "features": int(features.shape[1]),
        "train_rows": int(len(x_train)),
        "test_rows": int(len(x_test)),
        "rmse_days": model_rmse,
        "mae_days": model_mae,
        "r2": float(r2_score(y_test, prediction)),
        "actual_mean_days_test": actual_mean,
        "prediction_mean_days_test": prediction_mean,
        "train_mean_baseline_rmse_days": baseline_rmse,
        "train_mean_baseline_mae_days": baseline_mae,
        "rmse_improvement_vs_baseline_pct": (baseline_rmse - model_rmse) / baseline_rmse * 100,
        "mae_improvement_vs_baseline_pct": (baseline_mae - model_mae) / baseline_mae * 100,
        "mae_share_of_mean_delivery_pct": model_mae / actual_mean * 100,
        "rmse_share_of_mean_delivery_pct": model_rmse / actual_mean * 100,
        "mean_prediction_gap_days": prediction_mean - actual_mean,
        "mean_prediction_gap_pct": (prediction_mean - actual_mean) / actual_mean * 100,
    }


def repeat_purchase_gate(limit: int = 50_000) -> dict[str, Any]:
    """Return class-balance diagnostics for the repeat-purchase candidate."""
    _, target = get_churn_data(limit=limit)
    counts = target.value_counts().sort_index()
    return {
        "rows": int(len(target)),
        "class_counts": {str(int(key)): int(value) for key, value in counts.items()},
        "risk_label_share_pct": float(target.mean() * 100),
        "usable_for_model_eval": bool(has_usable_class_balance(target)),
    }


def recommender_benchmark(top_k: int = 10) -> dict[str, Any]:
    """Return offline recommender metrics and random-catalog baseline."""
    interactions = get_recommender_data(limit=None)
    evaluation = evaluate_leave_one_out(interactions, top_k=top_k)
    random_hit_rate = top_k / interactions["product_id"].nunique()
    hit_rate = float(evaluation["hit_rate_at_k"])

    return {
        "interactions": int(len(interactions)),
        "users": int(interactions["customer_id"].nunique()),
        "products": int(interactions["product_id"].nunique()),
        "users_evaluated": int(evaluation["users_evaluated"]),
        "hit_rate_at_k": hit_rate,
        "catalog_coverage_at_k": float(evaluation["catalog_coverage_at_k"]),
        "random_catalog_hit_rate_at_k": float(random_hit_rate),
        "lift_vs_random_catalog": float(hit_rate / random_hit_rate if random_hit_rate else 0.0),
    }


def build_summary() -> dict[str, Any]:
    return {
        "important_boundary": (
            "These are model/analytics benchmark results, not measured business "
            "impact from a live operation or A/B test."
        ),
        "delivery_prediction": delivery_benchmark(),
        "repeat_purchase_candidate": repeat_purchase_gate(),
        "recommender": recommender_benchmark(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Print indented JSON for human review.",
    )
    args = parser.parse_args()

    indent = 2 if args.pretty else None
    print(json.dumps(build_summary(), ensure_ascii=False, indent=indent))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
