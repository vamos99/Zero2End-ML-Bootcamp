"""Compute measured Olist benchmark results without writing model artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.ml.data import get_churn_data, get_db_engine, get_logistics_data, get_recommender_data  # noqa: E402
from src.ml.evaluation import has_usable_class_balance, temporal_train_test_split  # noqa: E402
from src.ml.recommender import evaluate_leave_one_out  # noqa: E402


def _rmse(actual, predicted) -> float:
    return float(np.sqrt(mean_squared_error(actual, predicted)))


def source_business_baselines() -> dict[str, Any]:
    """
    Return observed source-data baselines before any model intervention.

    These values describe the historical Olist snapshot. They are not
    before/after impact results because the public dataset has no treatment log,
    control group, or post-model operating period.
    """
    delivery_query = """
    SELECT
        JULIANDAY(order_delivered_customer_date) - JULIANDAY(order_purchase_timestamp)
            AS actual_delivery_days,
        JULIANDAY(order_estimated_delivery_date) - JULIANDAY(order_purchase_timestamp)
            AS estimated_delivery_days,
        CASE
            WHEN DATE(order_delivered_customer_date) > DATE(order_estimated_delivery_date)
            THEN 1 ELSE 0
        END AS is_late,
        CASE
            WHEN DATE(order_delivered_customer_date) > DATE(order_estimated_delivery_date)
            THEN JULIANDAY(DATE(order_delivered_customer_date))
               - JULIANDAY(DATE(order_estimated_delivery_date))
            ELSE 0
        END AS days_late
    FROM orders
    WHERE order_status = 'delivered'
      AND order_delivered_customer_date IS NOT NULL
      AND order_estimated_delivery_date IS NOT NULL
      AND JULIANDAY(order_delivered_customer_date) > JULIANDAY(order_purchase_timestamp)
    """
    repeat_query = """
    SELECT
        c.customer_unique_id,
        COUNT(DISTINCT o.order_id) AS delivered_orders
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id
    """
    engine = get_db_engine()
    with engine.connect() as conn:
        delivery = pd.read_sql(text(delivery_query), conn)
        repeat = pd.read_sql(text(repeat_query), conn)

    is_late = delivery["is_late"] == 1
    repeat_customers = repeat["delivered_orders"] > 1

    return {
        "boundary": (
            "Observed source-data baselines only. They quantify opportunity size, "
            "not improvement caused by this project."
        ),
        "delivery": {
            "delivered_orders": int(len(delivery)),
            "late_orders": int(is_late.sum()),
            "late_delivery_rate_pct": float(is_late.mean() * 100),
            "avg_actual_delivery_days": float(delivery["actual_delivery_days"].mean()),
            "median_actual_delivery_days": float(delivery["actual_delivery_days"].median()),
            "avg_estimated_delivery_days": float(delivery["estimated_delivery_days"].mean()),
            "avg_days_late_when_late": float(delivery.loc[is_late, "days_late"].mean()),
        },
        "repeat_purchase": {
            "unique_customers": int(len(repeat)),
            "repeat_customers": int(repeat_customers.sum()),
            "one_time_customers": int((~repeat_customers).sum()),
            "repeat_customer_rate_pct": float(repeat_customers.mean() * 100),
            "one_time_customer_rate_pct": float((~repeat_customers).mean() * 100),
        },
    }


def delivery_benchmark(limit: int = 50_000) -> dict[str, Any]:
    """Return temporal holdout metrics and naive-baseline comparison."""
    features, target, timestamps, estimated_days = get_logistics_data(
        limit=limit,
        include_timestamps=True,
        include_estimates=True,
    )
    target_frame = pd.DataFrame(
        {
            "actual_days": target,
            "estimated_days": estimated_days,
        }
    )
    x_train, x_test, y_train_frame, y_test_frame = temporal_train_test_split(
        features,
        target_frame,
        timestamps,
        test_size=0.2,
    )
    y_train = y_train_frame["actual_days"]
    y_test = y_test_frame["actual_days"]
    source_estimate = y_test_frame["estimated_days"]

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
    source_estimate_rmse = _rmse(y_test, source_estimate)
    model_mae = float(mean_absolute_error(y_test, prediction))
    baseline_mae = float(mean_absolute_error(y_test, baseline_prediction))
    source_estimate_mae = float(mean_absolute_error(y_test, source_estimate))
    actual_mean = float(np.mean(y_test))
    prediction_mean = float(np.mean(prediction))
    source_estimate_mean = float(np.mean(source_estimate))

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
        "source_estimate_mean_days_test": source_estimate_mean,
        "train_mean_baseline_rmse_days": baseline_rmse,
        "train_mean_baseline_mae_days": baseline_mae,
        "source_estimate_rmse_days": source_estimate_rmse,
        "source_estimate_mae_days": source_estimate_mae,
        "rmse_improvement_vs_baseline_pct": (baseline_rmse - model_rmse) / baseline_rmse * 100,
        "mae_improvement_vs_baseline_pct": (baseline_mae - model_mae) / baseline_mae * 100,
        "rmse_improvement_vs_source_estimate_pct": (
            source_estimate_rmse - model_rmse
        )
        / source_estimate_rmse
        * 100,
        "mae_improvement_vs_source_estimate_pct": (
            source_estimate_mae - model_mae
        )
        / source_estimate_mae
        * 100,
        "mae_share_of_mean_delivery_pct": model_mae / actual_mean * 100,
        "rmse_share_of_mean_delivery_pct": model_rmse / actual_mean * 100,
        "mean_prediction_gap_days": prediction_mean - actual_mean,
        "mean_prediction_gap_pct": (prediction_mean - actual_mean) / actual_mean * 100,
        "source_estimate_gap_days": source_estimate_mean - actual_mean,
        "source_estimate_gap_pct": (source_estimate_mean - actual_mean) / actual_mean * 100,
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


def intervention_scenarios(source_baselines: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Return transparent what-if scenarios for future business-impact measurement.

    These are assumption-driven projections, not measured post-model outcomes.
    They make the portfolio story concrete without pretending that an
    intervention has already happened.
    """
    baselines = source_baselines or source_business_baselines()
    delivery = baselines["delivery"]
    repeat = baselines["repeat_purchase"]

    delivery_rows = []
    for reduction_pct in (10, 20):
        prevented_late_orders = delivery["late_orders"] * reduction_pct / 100
        projected_late_orders = delivery["late_orders"] - prevented_late_orders
        projected_late_rate = projected_late_orders / delivery["delivered_orders"] * 100
        delivery_rows.append(
            {
                "assumption": f"{reduction_pct}% of late deliveries prevented",
                "baseline_late_rate_pct": delivery["late_delivery_rate_pct"],
                "projected_late_rate_pct": projected_late_rate,
                "late_rate_delta_pp": projected_late_rate
                - delivery["late_delivery_rate_pct"],
                "prevented_late_orders": prevented_late_orders,
                "potential_late_days_avoided": prevented_late_orders
                * delivery["avg_days_late_when_late"],
            }
        )

    repeat_rows = []
    for uplift_pp in (0.5, 1.0, 2.0):
        projected_repeat_rate = min(100.0, repeat["repeat_customer_rate_pct"] + uplift_pp)
        additional_repeat_customers = repeat["unique_customers"] * uplift_pp / 100
        repeat_rows.append(
            {
                "assumption": f"+{uplift_pp:.1f} percentage point repeat-customer uplift",
                "baseline_repeat_rate_pct": repeat["repeat_customer_rate_pct"],
                "projected_repeat_rate_pct": projected_repeat_rate,
                "repeat_rate_delta_pp": uplift_pp,
                "additional_repeat_customers": additional_repeat_customers,
            }
        )

    return {
        "boundary": (
            "Assumption-based planning scenarios only. Validate with A/B tests, "
            "holdouts, or post-intervention logs before calling them impact."
        ),
        "delivery": delivery_rows,
        "repeat_purchase": repeat_rows,
    }


def build_summary() -> dict[str, Any]:
    baselines = source_business_baselines()
    return {
        "important_boundary": (
            "These are model/analytics benchmark results, not measured business "
            "impact from a live operation or A/B test."
        ),
        "source_business_baselines": baselines,
        "delivery_prediction": delivery_benchmark(),
        "repeat_purchase_candidate": repeat_purchase_gate(),
        "recommender": recommender_benchmark(),
        "intervention_scenarios": intervention_scenarios(baselines),
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
