import pytest
from src.services.action_service import simulate_impact

def test_simulate_impact_known_action():
    """Known actions expose an experiment outcome, not invented ROI."""
    action = "%15 İndirim Tanımla"
    api_response = simulate_impact(action)
    
    assert api_response["hypothesis"] == "Reactivation conversion rate"
    assert "roi" not in api_response

def test_simulate_impact_unknown_action():
    """Test that unknown actions return default values."""
    action = "Unknown Action"
    api_response = simulate_impact(action)
    
    assert api_response["hypothesis"] == "Define before launch"
