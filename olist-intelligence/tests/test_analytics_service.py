import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from src.services import analytics_service

@patch('src.services.analytics_service.repository')
def test_get_daily_pulse(mock_repository):
    """Test get_daily_pulse aggregation."""
    # Setup Mocks
    mock_repository.get_total_orders.return_value = 1000
    mock_repository.get_logistics_risk_count.return_value = 50
    mock_repository.get_churn_risk_count.return_value = 200
    
    # Execute
    result = analytics_service.get_daily_pulse("2017-01-01", "2017-01-31")
    
    # Assert
    assert result["total_orders"] == 1000
    assert result["risk_logistics"] == 50
    assert result["risk_churn"] == 200
    
    # Verify calls
    mock_repository.get_total_orders.assert_called_once()
    mock_repository.get_logistics_risk_count.assert_called_once()

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
