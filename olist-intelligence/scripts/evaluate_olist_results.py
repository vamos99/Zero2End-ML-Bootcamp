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


def analytics_operating_signals() -> dict[str, Any]:
    """Return source-backed SQL mart and generated-output coverage signals."""
    queries = {
        "payment": """
            SELECT
                payment_type,
                SUM(payment_value) AS payment_value,
                SUM(orders) AS orders
            FROM payment_mix_summary
            GROUP BY payment_type
            ORDER BY payment_value DESC
        """,
        "cohort": """
            SELECT
                months_since_first_order,
                AVG(retention_rate) AS avg_retention_rate
            FROM customer_cohort_retention
            WHERE months_since_first_order IN (1, 2)
            GROUP BY months_since_first_order
        """,
        "seller": """
            SELECT
                COUNT(*) AS seller_rows,
                AVG(late_delivery_rate) AS avg_late_delivery_rate,
                MAX(late_delivery_rate) AS max_late_delivery_rate
            FROM seller_sla_summary
        """,
        "category": """
            SELECT
                category,
                orders,
                items,
                product_revenue,
                avg_review_score,
                late_delivery_rate
            FROM category_performance_summary
            ORDER BY product_revenue DESC
        """,
        "location": """
            SELECT
                customer_state,
                seller_state,
                lane_type,
                orders,
                product_revenue,
                avg_review_score,
                avg_delivery_days,
                late_delivery_rate,
                customer_geo_coverage_pct,
                seller_geo_coverage_pct
            FROM location_service_level_summary
            ORDER BY orders DESC
        """,
        "generated": """
            SELECT 'logistics_predictions' AS table_name, COUNT(*) AS rows FROM logistics_predictions
            UNION ALL
            SELECT 'customer_segments' AS table_name, COUNT(*) AS rows FROM customer_segments
        """,
        "segments": """
            SELECT
                "Segment" AS segment,
                COUNT(*) AS customers,
                AVG("Recency") AS avg_recency,
                AVG("Frequency") AS avg_frequency,
                AVG("Monetary") AS avg_monetary
            FROM customer_segments
            GROUP BY "Segment"
            ORDER BY customers DESC
        """,
    }

    engine = get_db_engine()
    try:
        with engine.connect() as conn:
            payment = pd.read_sql(text(queries["payment"]), conn)
            cohort = pd.read_sql(text(queries["cohort"]), conn)
            seller = pd.read_sql(text(queries["seller"]), conn)
            category = pd.read_sql(text(queries["category"]), conn)
            location = pd.read_sql(text(queries["location"]), conn)
            generated = pd.read_sql(text(queries["generated"]), conn)
            segments = pd.read_sql(text(queries["segments"]), conn)
    except Exception as exc:
        return {
            "available": False,
            "error": str(exc),
            "boundary": (
                "Analytics mart signals require SQL views plus generated logistics "
                "and segment outputs."
            ),
        }

    total_payment_value = float(payment["payment_value"].sum()) if not payment.empty else 0.0
    top_payment = payment.iloc[0].to_dict() if not payment.empty else {}
    top_payment_value = float(top_payment.get("payment_value", 0.0))
    top_payment_share = (
        top_payment_value / total_payment_value * 100
        if total_payment_value
        else 0.0
    )

    cohort_by_month = {
        int(row["months_since_first_order"]): float(row["avg_retention_rate"])
        for _, row in cohort.iterrows()
    }
    generated_counts = {
        str(row["table_name"]): int(row["rows"])
        for _, row in generated.iterrows()
    }
    largest_segment = segments.iloc[0].to_dict() if not segments.empty else {}
    total_category_revenue = (
        float(category["product_revenue"].sum()) if not category.empty else 0.0
    )
    top_category = category.iloc[0].to_dict() if not category.empty else {}
    top_category_revenue = float(top_category.get("product_revenue", 0.0))
    top_category_share = (
        top_category_revenue / total_category_revenue * 100
        if total_category_revenue
        else 0.0
    )
    total_location_orders = float(location["orders"].sum()) if not location.empty else 0.0
    same_state_orders = (
        float(location.loc[location["lane_type"] == "same_state", "orders"].sum())
        if not location.empty
        else 0.0
    )
    cross_state_orders = (
        float(location.loc[location["lane_type"] == "cross_state", "orders"].sum())
        if not location.empty
        else 0.0
    )
    cross_state_late_rate = (
        float(
            np.average(
                location.loc[location["lane_type"] == "cross_state", "late_delivery_rate"],
                weights=location.loc[location["lane_type"] == "cross_state", "orders"],
            )
        )
        if cross_state_orders
        else 0.0
    )
    top_location_lane = location.iloc[0].to_dict() if not location.empty else {}

    return {
        "available": True,
        "boundary": (
            "These are SQL mart and generated-output coverage signals, not "
            "post-intervention business impact."
        ),
        "payment_mix": {
            "methods": int(len(payment)),
            "total_payment_value_brl": total_payment_value,
            "top_payment_type": str(top_payment.get("payment_type", "")),
            "top_payment_value_brl": top_payment_value,
            "top_payment_share_pct": top_payment_share,
            "top_payment_orders": int(top_payment.get("orders", 0)),
        },
        "cohort_retention": {
            "month_1_avg_retention_pct": cohort_by_month.get(1, 0.0),
            "month_2_avg_retention_pct": cohort_by_month.get(2, 0.0),
        },
        "seller_sla": {
            "seller_rows": int(seller.iloc[0]["seller_rows"]) if not seller.empty else 0,
            "avg_late_delivery_rate_pct": float(seller.iloc[0]["avg_late_delivery_rate"])
            if not seller.empty and pd.notna(seller.iloc[0]["avg_late_delivery_rate"])
            else 0.0,
            "max_late_delivery_rate_pct": float(seller.iloc[0]["max_late_delivery_rate"])
            if not seller.empty and pd.notna(seller.iloc[0]["max_late_delivery_rate"])
            else 0.0,
        },
        "category_performance": {
            "top_categories_ranked": int(len(category)),
            "top_category": str(top_category.get("category", "")),
            "top_category_revenue_brl": top_category_revenue,
            "top_category_revenue_share_pct": top_category_share,
            "top_category_orders": int(top_category.get("orders", 0)),
            "top_category_avg_review_score": float(top_category.get("avg_review_score", 0.0)),
            "top_category_late_delivery_rate_pct": float(
                top_category.get("late_delivery_rate", 0.0)
            ),
        },
        "location_service": {
            "lanes": int(len(location)),
            "same_state_order_share_pct": (
                same_state_orders / total_location_orders * 100
                if total_location_orders
                else 0.0
            ),
            "cross_state_order_share_pct": (
                cross_state_orders / total_location_orders * 100
                if total_location_orders
                else 0.0
            ),
            "cross_state_late_delivery_rate_pct": cross_state_late_rate,
            "top_lane": (
                f"{top_location_lane.get('seller_state', '')}->{top_location_lane.get('customer_state', '')}"
                if top_location_lane
                else ""
            ),
            "top_lane_orders": int(top_location_lane.get("orders", 0)),
            "top_lane_late_delivery_rate_pct": float(
                top_location_lane.get("late_delivery_rate", 0.0)
            ),
            "customer_geo_coverage_pct": float(
                np.average(location["customer_geo_coverage_pct"], weights=location["orders"])
            )
            if total_location_orders
            else 0.0,
            "seller_geo_coverage_pct": float(
                np.average(location["seller_geo_coverage_pct"], weights=location["orders"])
            )
            if total_location_orders
            else 0.0,
        },
        "generated_outputs": generated_counts,
        "segmentation": {
            "segments": int(len(segments)),
            "customers": int(segments["customers"].sum()) if not segments.empty else 0,
            "largest_segment": str(largest_segment.get("segment", "")),
            "largest_segment_customers": int(largest_segment.get("customers", 0)),
        },
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


def _fmt_pct(value: float) -> str:
    return f"{value:.2f}%"


def _fmt_days(value: float) -> str:
    return f"{value:.2f} days"


def build_evidence_rows(summary: dict[str, Any]) -> list[dict[str, str]]:
    """
    Return a compact, reader-facing evidence table.

    The rows intentionally separate source baselines, model benchmarks,
    scenario targets, and missing business-impact evidence. This avoids turning
    an offline prediction gain into a false "delivery improved by X%" claim.
    """
    source = summary["source_business_baselines"]
    delivery_source = source["delivery"]
    repeat_source = source["repeat_purchase"]
    delivery_model = summary["delivery_prediction"]
    repeat_gate = summary["repeat_purchase_candidate"]
    recommender = summary["recommender"]
    analytics = summary["analytics_operating_signals"]
    scenarios = summary["intervention_scenarios"]
    if analytics.get("available") is False:
        analytics_row = {
            "area": "Executive analytics marts",
            "evidence_type": "analytics_mart_signal",
            "before_or_current": "Analytics mart signals unavailable",
            "model_or_target_result": "Run SQL mart and generated-output workflow",
            "delta_or_lift": "Not measured",
            "safe_claim": analytics.get(
                "boundary",
                "SQL marts and generated outputs are required before claiming dashboard coverage.",
            ),
        }
    else:
        analytics_row = {
            "area": "Executive analytics marts",
            "evidence_type": "analytics_mart_signal",
            "before_or_current": (
                f"Top payment: {analytics.get('payment_mix', {}).get('top_payment_type', '')}; "
                f"month-1 retention {_fmt_pct(analytics.get('cohort_retention', {}).get('month_1_avg_retention_pct', 0.0))}"
            ),
            "model_or_target_result": (
                f"{analytics.get('seller_sla', {}).get('seller_rows', 0):,} seller SLA rows; "
                f"{analytics.get('segmentation', {}).get('customers', 0):,} segmented customers; "
                f"top category {analytics.get('category_performance', {}).get('top_category', '')}; "
                f"top lane {analytics.get('location_service', {}).get('top_lane', '')}"
            ),
            "delta_or_lift": "No intervention delta measured",
            "safe_claim": "SQL marts and generated outputs support dashboard analysis, not impact claims.",
        }

    delivery_10pct = scenarios["delivery"][0]
    repeat_1pp = scenarios["repeat_purchase"][1]

    return [
        {
            "area": "Delivery source baseline",
            "evidence_type": "observed_source_baseline",
            "before_or_current": (
                f"{_fmt_pct(delivery_source['late_delivery_rate_pct'])} late delivery rate; "
                f"{_fmt_days(delivery_source['avg_actual_delivery_days'])} average delivery time"
            ),
            "model_or_target_result": "No post-intervention delivery-time measurement",
            "delta_or_lift": "Not measured",
            "safe_claim": "Quantifies the logistics opportunity size.",
        },
        {
            "area": "Delivery prediction benchmark",
            "evidence_type": "offline_model_benchmark",
            "before_or_current": (
                f"Train-mean MAE {_fmt_days(delivery_model['train_mean_baseline_mae_days'])}; "
                f"Olist estimated-date MAE {_fmt_days(delivery_model['source_estimate_mae_days'])}"
            ),
            "model_or_target_result": f"CatBoost MAE {_fmt_days(delivery_model['mae_days'])}",
            "delta_or_lift": (
                f"{_fmt_pct(delivery_model['mae_improvement_vs_baseline_pct'])} lower MAE vs train mean; "
                f"{_fmt_pct(delivery_model['mae_improvement_vs_source_estimate_pct'])} lower MAE vs estimated-date baseline"
            ),
            "safe_claim": "Prediction error improved; actual delivery speed did not get proven faster.",
        },
        {
            "area": "Repeat-purchase source baseline",
            "evidence_type": "observed_source_baseline",
            "before_or_current": (
                f"{_fmt_pct(repeat_source['repeat_customer_rate_pct'])} repeat customers; "
                f"{_fmt_pct(repeat_source['one_time_customer_rate_pct'])} one-time customers"
            ),
            "model_or_target_result": "No measured retention campaign result",
            "delta_or_lift": "Not measured",
            "safe_claim": "Cohort/retention analytics are stronger than a churn model on this snapshot.",
        },
        {
            "area": "Repeat-purchase / churn gate",
            "evidence_type": "model_readiness_gate",
            "before_or_current": (
                f"{_fmt_pct(repeat_gate['risk_label_share_pct'])} positive risk label share; "
                f"{repeat_gate['class_counts']} class counts"
            ),
            "model_or_target_result": (
                "Model evaluation gate passed"
                if repeat_gate["usable_for_model_eval"]
                else "Model evaluation gate failed"
            ),
            "delta_or_lift": "No churn reduction measured",
            "safe_claim": "Treat as a suitability check, not a deployed churn-impact result.",
        },
        {
            "area": "Recommender benchmark",
            "evidence_type": "offline_model_benchmark",
            "before_or_current": (
                f"Random catalog hit@10 {_fmt_pct(recommender['random_catalog_hit_rate_at_k'] * 100)}"
            ),
            "model_or_target_result": f"SVD hit@10 {_fmt_pct(recommender['hit_rate_at_k'] * 100)}",
            "delta_or_lift": f"{recommender['lift_vs_random_catalog']:.1f}x random baseline",
            "safe_claim": "Ranking quality beat random; sales or basket uplift was not measured.",
        },
        analytics_row,
        {
            "area": "Delivery scenario target",
            "evidence_type": "planning_scenario",
            "before_or_current": _fmt_pct(delivery_10pct["baseline_late_rate_pct"]),
            "model_or_target_result": _fmt_pct(delivery_10pct["projected_late_rate_pct"]),
            "delta_or_lift": (
                f"{delivery_10pct['late_rate_delta_pp']:.2f} pp; "
                f"{delivery_10pct['prevented_late_orders']:.0f} fewer late orders if validated"
            ),
            "safe_claim": "A target for future experiment design, not a result that already happened.",
        },
        {
            "area": "Repeat-purchase scenario target",
            "evidence_type": "planning_scenario",
            "before_or_current": _fmt_pct(repeat_1pp["baseline_repeat_rate_pct"]),
            "model_or_target_result": _fmt_pct(repeat_1pp["projected_repeat_rate_pct"]),
            "delta_or_lift": (
                f"+{repeat_1pp['repeat_rate_delta_pp']:.1f} pp; "
                f"{repeat_1pp['additional_repeat_customers']:.0f} more repeat customers if validated"
            ),
            "safe_claim": "A target for future campaign measurement, not measured churn improvement.",
        },
    ]


def build_outcome_scorecard(summary: dict[str, Any]) -> list[dict[str, str]]:
    """Return plain-language before/current/result rows for portfolio readers."""
    source = summary["source_business_baselines"]
    delivery_source = source["delivery"]
    repeat_source = source["repeat_purchase"]
    delivery_model = summary["delivery_prediction"]
    repeat_gate = summary["repeat_purchase_candidate"]
    recommender = summary["recommender"]
    analytics = summary["analytics_operating_signals"]
    delivery_10pct = summary["intervention_scenarios"]["delivery"][0]
    repeat_1pp = summary["intervention_scenarios"]["repeat_purchase"][1]

    if analytics.get("available") is False:
        analytics_current = "Analytics marts unavailable"
    else:
        analytics_current = (
            f"{analytics.get('seller_sla', {}).get('seller_rows', 0):,} seller SLA rows; "
            f"{analytics.get('segmentation', {}).get('customers', 0):,} segmented customers; "
            f"month-1 retention {_fmt_pct(analytics.get('cohort_retention', {}).get('month_1_avg_retention_pct', 0.0))}; "
            f"top category {analytics.get('category_performance', {}).get('top_category', '')}; "
            f"top lane {analytics.get('location_service', {}).get('top_lane', '')}"
        )

    return [
        {
            "area": "Actual delivery operation",
            "before": (
                f"{_fmt_days(delivery_source['avg_actual_delivery_days'])} avg delivery; "
                f"{_fmt_pct(delivery_source['late_delivery_rate_pct'])} late rate"
            ),
            "current_or_model_result": "No post-intervention operating period in the dataset",
            "measured_change": "No actual delivery-time improvement measured",
            "status": "source baseline only",
        },
        {
            "area": "Delivery prediction",
            "before": (
                f"Train-mean MAE {_fmt_days(delivery_model['train_mean_baseline_mae_days'])}; "
                f"Olist estimated-date MAE {_fmt_days(delivery_model['source_estimate_mae_days'])}"
            ),
            "current_or_model_result": f"CatBoost MAE {_fmt_days(delivery_model['mae_days'])}",
            "measured_change": (
                f"{_fmt_pct(delivery_model['mae_improvement_vs_baseline_pct'])} lower MAE vs train mean; "
                f"{_fmt_pct(delivery_model['mae_improvement_vs_source_estimate_pct'])} lower MAE vs Olist estimated-date baseline"
            ),
            "status": "offline prediction benchmark improved",
        },
        {
            "area": "Repeat purchase / churn",
            "before": (
                f"{_fmt_pct(repeat_source['repeat_customer_rate_pct'])} repeat customers; "
                f"{_fmt_pct(repeat_source['one_time_customer_rate_pct'])} one-time customers"
            ),
            "current_or_model_result": (
                "Model gate passed"
                if repeat_gate["usable_for_model_eval"]
                else "Model gate failed because the label distribution is too imbalanced"
            ),
            "measured_change": "No churn or retention uplift measured",
            "status": "use cohort retention and experiment design before impact claims",
        },
        {
            "area": "Recommendation quality",
            "before": f"Random catalog hit@10 {_fmt_pct(recommender['random_catalog_hit_rate_at_k'] * 100)}",
            "current_or_model_result": f"SVD hit@10 {_fmt_pct(recommender['hit_rate_at_k'] * 100)}",
            "measured_change": f"{recommender['lift_vs_random_catalog']:.1f}x random baseline",
            "status": "offline ranking benchmark improved; sales uplift not measured",
        },
        {
            "area": "Executive analytics coverage",
            "before": "Raw Olist tables only",
            "current_or_model_result": analytics_current,
            "measured_change": "Dashboard evidence coverage improved, not business outcome",
            "status": "SQL mart and generated-output coverage",
        },
        {
            "area": "Delivery scenario target",
            "before": _fmt_pct(delivery_10pct["baseline_late_rate_pct"]),
            "current_or_model_result": _fmt_pct(delivery_10pct["projected_late_rate_pct"]),
            "measured_change": (
                f"{delivery_10pct['late_rate_delta_pp']:.2f} pp target; "
                f"{delivery_10pct['prevented_late_orders']:.0f} late orders if validated"
            ),
            "status": "future experiment target, not measured impact",
        },
        {
            "area": "Repeat-purchase scenario target",
            "before": _fmt_pct(repeat_1pp["baseline_repeat_rate_pct"]),
            "current_or_model_result": _fmt_pct(repeat_1pp["projected_repeat_rate_pct"]),
            "measured_change": (
                f"+{repeat_1pp['repeat_rate_delta_pp']:.1f} pp target; "
                f"{repeat_1pp['additional_repeat_customers']:.0f} repeat customers if validated"
            ),
            "status": "future experiment target, not measured impact",
        },
    ]


def build_plain_language_answers(summary: dict[str, Any]) -> list[dict[str, str]]:
    """
    Answer the common "what improved?" questions without overstating impact.

    The public Olist snapshot has no treatment/control group or post-model
    operating period. Therefore, only offline benchmark gains and explicit
    scenario targets can be expressed as before/current deltas.
    """
    delivery_source = summary["source_business_baselines"]["delivery"]
    repeat_source = summary["source_business_baselines"]["repeat_purchase"]
    delivery_model = summary["delivery_prediction"]
    repeat_gate = summary["repeat_purchase_candidate"]
    recommender = summary["recommender"]
    delivery_10pct = summary["intervention_scenarios"]["delivery"][0]
    repeat_1pp = summary["intervention_scenarios"]["repeat_purchase"][1]

    return [
        {
            "question": "Teslim süresi ne kadar iyileşti?",
            "short_answer": "Gerçek teslim süresi iyileşmesi ölçülmedi.",
            "numeric_evidence": (
                f"Kaynak baseline {_fmt_days(delivery_source['avg_actual_delivery_days'])} "
                f"ortalama teslimat ve {_fmt_pct(delivery_source['late_delivery_rate_pct'])} "
                "geç teslimat oranıdır."
            ),
            "what_changed": (
                f"Tahmin kalitesi iyileşti: CatBoost MAE {_fmt_days(delivery_model['mae_days'])}; "
                f"train-mean baseline'a göre {_fmt_pct(delivery_model['mae_improvement_vs_baseline_pct'])}, "
                f"Olist estimated-date baseline'a göre "
                f"{_fmt_pct(delivery_model['mae_improvement_vs_source_estimate_pct'])} daha düşük hata."
            ),
            "claim_boundary": (
                "Bu, teslimat operasyonunun hızlandığı anlamına gelmez; sadece "
                "offline tahmin benchmark'ının iyileştiğini gösterir."
            ),
        },
        {
            "question": "Churn veya retention ne kadar iyileşti?",
            "short_answer": "Churn/retention uplift ölçülmedi.",
            "numeric_evidence": (
                f"Kaynak repeat-customer oranı {_fmt_pct(repeat_source['repeat_customer_rate_pct'])}; "
                f"one-time customer oranı {_fmt_pct(repeat_source['one_time_customer_rate_pct'])}. "
                f"Risk label share {_fmt_pct(repeat_gate['risk_label_share_pct'])}."
            ),
            "what_changed": (
                "Churn modeli başarı diye sunulmadı; sınıf dengesi uygun olmadığı için "
                "model evaluation gate başarısız olarak raporlandı."
            ),
            "claim_boundary": (
                "Bu alan için doğru sonraki adım cohort retention ve kontrollü kampanya "
                "deneyi kurmaktır."
            ),
        },
        {
            "question": "Recommendation tarafında ne iyileşti?",
            "short_answer": "Satış uplift'i değil, offline ranking benchmark'ı iyileşti.",
            "numeric_evidence": (
                f"Random catalog hit@10 {_fmt_pct(recommender['random_catalog_hit_rate_at_k'] * 100)}; "
                f"SVD hit@10 {_fmt_pct(recommender['hit_rate_at_k'] * 100)}."
            ),
            "what_changed": (
                f"SVD recommender random catalog baseline'a göre "
                f"{recommender['lift_vs_random_catalog']:.1f}x lift üretti."
            ),
            "claim_boundary": "Sepet, gelir veya dönüşüm artışı ölçülmedi.",
        },
        {
            "question": "Peki önce/sonra yüzdesi hiç yok mu?",
            "short_answer": "Var, ama gerçekleşmiş impact değil; planlama scenario'su olarak var.",
            "numeric_evidence": (
                f"10% late-delivery prevention scenario'su geç teslimat oranını "
                f"{_fmt_pct(delivery_10pct['baseline_late_rate_pct'])} -> "
                f"{_fmt_pct(delivery_10pct['projected_late_rate_pct'])} hedefler. "
                f"+1 pp repeat scenario'su repeat oranını "
                f"{_fmt_pct(repeat_1pp['baseline_repeat_rate_pct'])} -> "
                f"{_fmt_pct(repeat_1pp['projected_repeat_rate_pct'])} hedefler."
            ),
            "what_changed": (
                f"Bu hedefler sırasıyla {delivery_10pct['prevented_late_orders']:.0f} "
                f"geç siparişin önlenmesi ve {repeat_1pp['additional_repeat_customers']:.0f} "
                "ek repeat customer anlamına gelir."
            ),
            "claim_boundary": (
                "Bu sayılar A/B test, holdout kampanya veya operasyon loguyla doğrulanmadan "
                "gerçekleşmiş iyileşme diye yazılmamalıdır."
            ),
        },
    ]


def build_summary() -> dict[str, Any]:
    baselines = source_business_baselines()
    summary = {
        "important_boundary": (
            "These are model/analytics benchmark results, not measured business "
            "impact from a live operation or A/B test."
        ),
        "source_business_baselines": baselines,
        "delivery_prediction": delivery_benchmark(),
        "repeat_purchase_candidate": repeat_purchase_gate(),
        "recommender": recommender_benchmark(),
        "analytics_operating_signals": analytics_operating_signals(),
        "intervention_scenarios": intervention_scenarios(baselines),
    }
    summary["evidence_rows"] = build_evidence_rows(summary)
    summary["outcome_scorecard"] = build_outcome_scorecard(summary)
    summary["plain_language_answers"] = build_plain_language_answers(summary)
    return summary


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
