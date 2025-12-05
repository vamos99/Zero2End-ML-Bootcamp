import pytest
from src.services.action_service import simulate_impact

def test_simulate_impact_known_action():
    """Test that known actions return correct ROI data."""
    action = "%15 İndirim Tanımla"
    api_response = simulate_impact(action)
    
    assert api_response["cost"] == 5000
    assert api_response["saved"] == 120000
    assert api_response["roi"] == "%2400"

def test_simulate_impact_unknown_action():
    """Test that unknown actions return default values."""
    action = "Unknown Action"
    api_response = simulate_impact(action)
    
    assert api_response["cost"] == 0
    assert api_response["roi"] == "N/A"
