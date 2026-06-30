from unittest.mock import MagicMock

import pandas as pd

from scripts import evaluate_olist_results


def test_source_business_baselines_calculate_observed_opportunity(monkeypatch):
    delivery_rows = pd.DataFrame(
        {
            "actual_delivery_days": [5.0, 8.0, 12.0],
            "estimated_delivery_days": [7.0, 7.0, 10.0],
            "is_late": [0, 1, 1],
            "days_late": [0.0, 1.0, 2.0],
        }
    )
    repeat_rows = pd.DataFrame(
        {
            "customer_unique_id": ["c1", "c2", "c3"],
            "delivered_orders": [1, 2, 1],
        }
    )
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = MagicMock()

    monkeypatch.setattr(evaluate_olist_results, "get_db_engine", lambda: engine)
    monkeypatch.setattr(
        evaluate_olist_results.pd,
        "read_sql",
        MagicMock(side_effect=[delivery_rows, repeat_rows]),
    )

    result = evaluate_olist_results.source_business_baselines()

    assert result["delivery"]["delivered_orders"] == 3
    assert result["delivery"]["late_orders"] == 2
    assert result["delivery"]["late_delivery_rate_pct"] == 2 / 3 * 100
    assert result["delivery"]["avg_days_late_when_late"] == 1.5
    assert result["repeat_purchase"]["repeat_customers"] == 1
    assert result["repeat_purchase"]["one_time_customer_rate_pct"] == 2 / 3 * 100


def test_build_summary_includes_source_baselines(monkeypatch):
    monkeypatch.setattr(evaluate_olist_results, "source_business_baselines", lambda: {"ok": True})
    monkeypatch.setattr(evaluate_olist_results, "delivery_benchmark", lambda: {"delivery": True})
    monkeypatch.setattr(evaluate_olist_results, "repeat_purchase_gate", lambda: {"repeat": True})
    monkeypatch.setattr(evaluate_olist_results, "recommender_benchmark", lambda: {"recommender": True})
    monkeypatch.setattr(evaluate_olist_results, "analytics_operating_signals", lambda: {"analytics": True})
    monkeypatch.setattr(
        evaluate_olist_results,
        "intervention_scenarios",
        lambda baselines: {"from_baselines": baselines},
    )
    monkeypatch.setattr(evaluate_olist_results, "build_evidence_rows", lambda summary: [{"ok": True}])
    monkeypatch.setattr(evaluate_olist_results, "build_outcome_scorecard", lambda summary: [{"score": True}])

    result = evaluate_olist_results.build_summary()

    assert result["source_business_baselines"] == {"ok": True}
    assert result["intervention_scenarios"] == {"from_baselines": {"ok": True}}
    assert result["evidence_rows"] == [{"ok": True}]
    assert result["outcome_scorecard"] == [{"score": True}]
    assert result["analytics_operating_signals"] == {"analytics": True}
    assert "not measured business impact" in result["important_boundary"]


def test_analytics_operating_signals_summarize_sql_marts(monkeypatch):
    payment_rows = pd.DataFrame(
        {
            "payment_type": ["credit_card", "boleto"],
            "payment_value": [80.0, 20.0],
            "orders": [8, 2],
        }
    )
    cohort_rows = pd.DataFrame(
        {
            "months_since_first_order": [1, 2],
            "avg_retention_rate": [5.0, 1.0],
        }
    )
    seller_rows = pd.DataFrame(
        {
            "seller_rows": [3],
            "avg_late_delivery_rate": [8.5],
            "max_late_delivery_rate": [100.0],
        }
    )
    generated_rows = pd.DataFrame(
        {
            "table_name": ["logistics_predictions", "customer_segments"],
            "rows": [100, 50],
        }
    )
    segment_rows = pd.DataFrame(
        {
            "segment": ["Developing", "At Risk"],
            "customers": [30, 20],
            "avg_recency": [100.0, 300.0],
            "avg_frequency": [1.0, 1.1],
            "avg_monetary": [120.0, 130.0],
        }
    )
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = MagicMock()

    monkeypatch.setattr(evaluate_olist_results, "get_db_engine", lambda: engine)
    monkeypatch.setattr(
        evaluate_olist_results.pd,
        "read_sql",
        MagicMock(
            side_effect=[
                payment_rows,
                cohort_rows,
                seller_rows,
                generated_rows,
                segment_rows,
            ]
        ),
    )

    result = evaluate_olist_results.analytics_operating_signals()

    assert result["available"] is True
    assert result["payment_mix"]["top_payment_type"] == "credit_card"
    assert result["payment_mix"]["top_payment_share_pct"] == 80.0
    assert result["cohort_retention"]["month_1_avg_retention_pct"] == 5.0
    assert result["seller_sla"]["seller_rows"] == 3
    assert result["generated_outputs"]["logistics_predictions"] == 100
    assert result["segmentation"]["largest_segment"] == "Developing"


def test_evidence_rows_keep_benchmark_and_impact_separate():
    summary = {
        "source_business_baselines": {
            "delivery": {
                "late_delivery_rate_pct": 10.0,
                "avg_actual_delivery_days": 12.5,
            },
            "repeat_purchase": {
                "repeat_customer_rate_pct": 3.0,
                "one_time_customer_rate_pct": 97.0,
            },
        },
        "delivery_prediction": {
            "train_mean_baseline_mae_days": 8.0,
            "source_estimate_mae_days": 12.0,
            "mae_days": 6.0,
            "mae_improvement_vs_baseline_pct": 25.0,
            "mae_improvement_vs_source_estimate_pct": 50.0,
        },
        "repeat_purchase_candidate": {
            "risk_label_share_pct": 99.4,
            "class_counts": {"0": 298, "1": 49702},
            "usable_for_model_eval": False,
        },
        "recommender": {
            "random_catalog_hit_rate_at_k": 0.0003,
            "hit_rate_at_k": 0.035,
            "lift_vs_random_catalog": 116.0,
        },
        "analytics_operating_signals": {
            "payment_mix": {"top_payment_type": "credit_card"},
            "cohort_retention": {"month_1_avg_retention_pct": 5.0},
            "seller_sla": {"seller_rows": 2970},
            "segmentation": {"customers": 93358},
        },
        "intervention_scenarios": {
            "delivery": [
                {
                    "baseline_late_rate_pct": 10.0,
                    "projected_late_rate_pct": 9.0,
                    "late_rate_delta_pp": -1.0,
                    "prevented_late_orders": 100.0,
                }
            ],
            "repeat_purchase": [
                {"unused": True},
                {
                    "baseline_repeat_rate_pct": 3.0,
                    "projected_repeat_rate_pct": 4.0,
                    "repeat_rate_delta_pp": 1.0,
                    "additional_repeat_customers": 934.0,
                },
            ],
        },
    }

    rows = evaluate_olist_results.build_evidence_rows(summary)

    assert {row["evidence_type"] for row in rows} == {
        "observed_source_baseline",
        "offline_model_benchmark",
        "model_readiness_gate",
        "planning_scenario",
        "analytics_mart_signal",
    }
    delivery_benchmark = next(row for row in rows if row["area"] == "Delivery prediction benchmark")
    assert "50.00% lower MAE vs estimated-date baseline" in delivery_benchmark["delta_or_lift"]
    assert "actual delivery speed did not get proven faster" in delivery_benchmark["safe_claim"]
    churn_gate = next(row for row in rows if row["area"] == "Repeat-purchase / churn gate")
    assert churn_gate["model_or_target_result"] == "Model evaluation gate failed"
    assert churn_gate["delta_or_lift"] == "No churn reduction measured"
    analytics_row = next(row for row in rows if row["area"] == "Executive analytics marts")
    assert "credit_card" in analytics_row["before_or_current"]
    assert "seller SLA rows" in analytics_row["model_or_target_result"]


def test_evidence_rows_mark_missing_analytics_outputs_as_unavailable():
    summary = {
        "source_business_baselines": {
            "delivery": {
                "late_delivery_rate_pct": 5.0,
                "avg_actual_delivery_days": 12.0,
            },
            "repeat_purchase": {
                "repeat_customer_rate_pct": 3.0,
                "one_time_customer_rate_pct": 97.0,
            },
        },
        "delivery_prediction": {
            "train_mean_baseline_mae_days": 8.0,
            "source_estimate_mae_days": 12.0,
            "mae_days": 7.0,
            "mae_improvement_vs_baseline_pct": 12.5,
            "mae_improvement_vs_source_estimate_pct": 41.7,
        },
        "repeat_purchase_candidate": {
            "risk_label_share_pct": 99.0,
            "class_counts": {"0": 10, "1": 990},
            "usable_for_model_eval": False,
        },
        "recommender": {
            "random_catalog_hit_rate_at_k": 0.001,
            "hit_rate_at_k": 0.02,
            "lift_vs_random_catalog": 20.0,
        },
        "analytics_operating_signals": {
            "available": False,
            "boundary": "Analytics mart signals require generated outputs.",
        },
        "intervention_scenarios": {
            "delivery": [
                {
                    "baseline_late_rate_pct": 5.0,
                    "projected_late_rate_pct": 4.5,
                    "late_rate_delta_pp": -0.5,
                    "prevented_late_orders": 100,
                }
            ],
            "repeat_purchase": [
                {"unused": True},
                {
                    "baseline_repeat_rate_pct": 3.0,
                    "projected_repeat_rate_pct": 4.0,
                    "repeat_rate_delta_pp": 1.0,
                    "additional_repeat_customers": 900,
                },
            ],
        },
    }

    rows = evaluate_olist_results.build_evidence_rows(summary)

    analytics_row = next(row for row in rows if row["area"] == "Executive analytics marts")
    assert analytics_row["before_or_current"] == "Analytics mart signals unavailable"
    assert analytics_row["model_or_target_result"] == "Run SQL mart and generated-output workflow"
    assert "generated outputs" in analytics_row["safe_claim"]


def test_outcome_scorecard_answers_what_actually_improved():
    summary = {
        "source_business_baselines": {
            "delivery": {
                "avg_actual_delivery_days": 12.5,
                "late_delivery_rate_pct": 10.0,
            },
            "repeat_purchase": {
                "repeat_customer_rate_pct": 3.0,
                "one_time_customer_rate_pct": 97.0,
            },
        },
        "delivery_prediction": {
            "train_mean_baseline_mae_days": 8.0,
            "source_estimate_mae_days": 12.0,
            "mae_days": 6.0,
            "mae_improvement_vs_baseline_pct": 25.0,
            "mae_improvement_vs_source_estimate_pct": 50.0,
        },
        "repeat_purchase_candidate": {
            "usable_for_model_eval": False,
        },
        "recommender": {
            "random_catalog_hit_rate_at_k": 0.001,
            "hit_rate_at_k": 0.02,
            "lift_vs_random_catalog": 20.0,
        },
        "analytics_operating_signals": {
            "available": True,
            "seller_sla": {"seller_rows": 10},
            "segmentation": {"customers": 100},
            "cohort_retention": {"month_1_avg_retention_pct": 5.0},
        },
        "intervention_scenarios": {
            "delivery": [
                {
                    "baseline_late_rate_pct": 10.0,
                    "projected_late_rate_pct": 9.0,
                    "late_rate_delta_pp": -1.0,
                    "prevented_late_orders": 100,
                }
            ],
            "repeat_purchase": [
                {"unused": True},
                {
                    "baseline_repeat_rate_pct": 3.0,
                    "projected_repeat_rate_pct": 4.0,
                    "repeat_rate_delta_pp": 1.0,
                    "additional_repeat_customers": 900,
                },
            ],
        },
    }

    rows = evaluate_olist_results.build_outcome_scorecard(summary)

    delivery_actual = next(row for row in rows if row["area"] == "Actual delivery operation")
    assert delivery_actual["measured_change"] == "No actual delivery-time improvement measured"
    delivery_model = next(row for row in rows if row["area"] == "Delivery prediction")
    assert "50.00% lower MAE vs Olist estimated-date baseline" in delivery_model["measured_change"]
    churn = next(row for row in rows if row["area"] == "Repeat purchase / churn")
    assert churn["measured_change"] == "No churn or retention uplift measured"
    scenario = next(row for row in rows if row["area"] == "Delivery scenario target")
    assert scenario["status"] == "future experiment target, not measured impact"


def test_intervention_scenarios_are_explicit_assumption_based():
    baselines = {
        "delivery": {
            "delivered_orders": 1000,
            "late_orders": 100,
            "late_delivery_rate_pct": 10.0,
            "avg_days_late_when_late": 5.0,
        },
        "repeat_purchase": {
            "unique_customers": 2000,
            "repeat_customer_rate_pct": 3.0,
        },
    }

    result = evaluate_olist_results.intervention_scenarios(baselines)

    first_delivery = result["delivery"][0]
    assert first_delivery["assumption"] == "10% of late deliveries prevented"
    assert first_delivery["projected_late_rate_pct"] == 9.0
    assert first_delivery["prevented_late_orders"] == 10.0
    assert first_delivery["potential_late_days_avoided"] == 50.0

    one_point_repeat = result["repeat_purchase"][1]
    assert one_point_repeat["assumption"] == "+1.0 percentage point repeat-customer uplift"
    assert one_point_repeat["projected_repeat_rate_pct"] == 4.0
    assert one_point_repeat["additional_repeat_customers"] == 20.0
    assert "Assumption-based" in result["boundary"]
