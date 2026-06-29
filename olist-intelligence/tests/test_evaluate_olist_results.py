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
    monkeypatch.setattr(
        evaluate_olist_results,
        "intervention_scenarios",
        lambda baselines: {"from_baselines": baselines},
    )
    monkeypatch.setattr(evaluate_olist_results, "build_evidence_rows", lambda summary: [{"ok": True}])

    result = evaluate_olist_results.build_summary()

    assert result["source_business_baselines"] == {"ok": True}
    assert result["intervention_scenarios"] == {"from_baselines": {"ok": True}}
    assert result["evidence_rows"] == [{"ok": True}]
    assert "not measured business impact" in result["important_boundary"]


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
    }
    delivery_benchmark = next(row for row in rows if row["area"] == "Delivery prediction benchmark")
    assert "50.00% lower MAE vs estimated-date baseline" in delivery_benchmark["delta_or_lift"]
    assert "actual delivery speed did not get proven faster" in delivery_benchmark["safe_claim"]
    churn_gate = next(row for row in rows if row["area"] == "Repeat-purchase / churn gate")
    assert churn_gate["model_or_target_result"] == "Model evaluation gate failed"
    assert churn_gate["delta_or_lift"] == "No churn reduction measured"


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
