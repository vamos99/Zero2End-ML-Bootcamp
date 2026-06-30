import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from src.services import analytics_service


def test_build_impact_scenario_summary():
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

    result = analytics_service.build_impact_scenario_summary(baselines)

    assert result["delivery_scenario"]["projected_late_rate_pct"] == 9.0
    assert result["delivery_scenario"]["prevented_late_orders"] == 10.0
    assert result["delivery_scenario"]["potential_late_days_avoided"] == 50.0
    assert result["repeat_purchase_scenario"]["projected_repeat_rate_pct"] == 4.0
    assert result["repeat_purchase_scenario"]["additional_repeat_customers"] == 20.0
    assert "not measured impact" in result["boundary"]


def test_build_dashboard_outcome_scorecard_separates_impact_from_targets():
    impact_summary = {
        "source_baselines": {
            "delivery": {"late_delivery_rate_pct": 10.0},
            "repeat_purchase": {
                "repeat_customer_rate_pct": 3.0,
                "one_time_customer_rate_pct": 97.0,
            },
        },
        "delivery_scenario": {
            "baseline_late_rate_pct": 10.0,
            "projected_late_rate_pct": 9.0,
            "late_rate_delta_pp": -1.0,
            "prevented_late_orders": 100.0,
        },
        "repeat_purchase_scenario": {
            "baseline_repeat_rate_pct": 3.0,
            "projected_repeat_rate_pct": 4.0,
            "additional_repeat_customers": 900.0,
        },
    }
    payment = pd.DataFrame({"payment_type": ["credit_card", "boleto"]})
    cohort = pd.DataFrame({"cohort_month": ["2017-01"]})
    sellers = pd.DataFrame({"seller_id": ["seller_1", "seller_2", "seller_3"]})

    result = analytics_service.build_dashboard_outcome_scorecard(
        impact_summary,
        payment_mix=payment,
        cohort_retention=cohort,
        seller_sla_watchlist=sellers,
    )

    delivery_actual = next(row for row in result if row["area"] == "Actual delivery operation")
    assert delivery_actual["measured_change"] == "No actual delivery-time improvement measured"
    delivery_target = next(row for row in result if row["area"] == "Delivery scenario target")
    assert delivery_target["status"] == "Future experiment target"
    churn = next(row for row in result if row["area"] == "Repeat purchase / churn")
    assert churn["measured_change"] == "No churn or retention uplift measured"
    coverage = next(row for row in result if row["area"] == "Executive analytics coverage")
    assert coverage["current_or_target"] == "2 payment methods; 1 cohort rows; 3 seller watchlist rows"


@patch('src.services.analytics_service.repository')
def test_get_daily_pulse(mock_repository):
    """Test get_daily_pulse aggregation."""
    # Setup Mocks
    mock_repository.get_total_orders.return_value = 1000
    mock_repository.get_logistics_risk_count.return_value = 50
    mock_repository.get_churn_risk_count.return_value = 200
    mock_repository.get_revenue_metrics.return_value = {
        "total_revenue": 25000.0,
        "avg_order_value": 25.0,
        "unique_customers": 800,
        "revenue_per_customer": 31.25,
    }
    mock_repository.get_review_delivery_quality.return_value = {
        "avg_review_score": 4.2,
        "late_delivery_rate": 8.5,
        "review_count": 900,
    }
    
    # Execute
    result = analytics_service.get_daily_pulse("2017-01-01", "2017-01-31")
    
    # Assert
    assert result["total_orders"] == 1000
    assert result["risk_logistics"] == 50
    assert result["risk_churn"] == 200
    assert result["total_revenue"] == 25000.0
    assert result["late_delivery_rate"] == 8.5
    
    # Verify calls
    mock_repository.get_total_orders.assert_called_once()
    mock_repository.get_logistics_risk_count.assert_called_once()

@patch('src.services.analytics_service.repository')
def test_get_executive_dashboard_data(mock_repository):
    """Test executive dashboard chart data preparation."""
    state_df = pd.DataFrame({"customer_state": ["SP"], "revenue": [1000], "order_count": [10]})
    quality_df = pd.DataFrame({"review_score": [5], "late_delivery_rate": [2.5], "order_count": [10]})
    payment_df = pd.DataFrame({"payment_type": ["credit_card"], "payment_value": [1000], "orders": [10]})
    cohort_df = pd.DataFrame({"cohort_month": ["2017-01"], "months_since_first_order": [1], "retention_rate": [2.5]})
    seller_df = pd.DataFrame({"seller_id": ["seller_123456789"], "late_delivery_rate": [45.0], "orders": [25]})

    mock_repository.get_revenue_by_state.return_value = state_df
    mock_repository.get_review_delivery_matrix.return_value = quality_df
    mock_repository.get_payment_mix_summary.return_value = payment_df
    mock_repository.get_cohort_retention_matrix.return_value = cohort_df
    mock_repository.get_seller_sla_watchlist.return_value = seller_df
    mock_repository.get_source_business_baselines.return_value = {
        "delivery": {
            "delivered_orders": 100,
            "late_orders": 10,
            "late_delivery_rate_pct": 10.0,
            "avg_days_late_when_late": 4.0,
        },
        "repeat_purchase": {
            "unique_customers": 500,
            "repeat_customer_rate_pct": 3.0,
            "one_time_customer_rate_pct": 97.0,
        },
    }

    result = analytics_service.get_executive_dashboard_data("2017-01-01", "2017-01-31")

    assert result["revenue_by_state"].equals(state_df)
    assert result["review_delivery_matrix"].equals(quality_df)
    assert result["payment_mix"].equals(payment_df)
    assert result["cohort_retention"].equals(cohort_df)
    assert result["seller_sla_watchlist"].iloc[0]["seller_label"] == "Seller seller_1..."
    assert result["impact_summary"]["delivery_scenario"]["projected_late_rate_pct"] == 9.0
    assert result["outcome_scorecard"][0]["area"] == "Actual delivery operation"

@patch('src.services.analytics_service.repository')
def test_get_logistics_data(mock_repository):
    """Test logistics data preparation and masking."""
    # Setup Mocks
    mock_repository.get_logistics_risk_count.return_value = 10
    mock_repository.get_logistics_metrics.return_value = {"on_time_rate": 95.0, "avg_time": 8.5}
    
    # Mock DataFrame
    df_mock = pd.DataFrame({
        "customer_id": ["1234567890", "0987654321"],
        "predicted_delivery_days": [12, 15],
        "delivery_days": [10, 14]
    })
    mock_repository.get_logistics_details.return_value = df_mock
    
    # Execute
    risk_count, metrics, df_details = analytics_service.get_logistics_data("2017-01-01", "2017-01-31")
    
    # Assert
    assert risk_count == 10
    assert metrics["on_time_rate"] == 95.0
    assert "Müşteri Kodu" in df_details.columns
    assert "customer_id" not in df_details.columns # Verify Masking
    assert df_details.iloc[0]["Müşteri Kodu"] == "CUST-12345..."
