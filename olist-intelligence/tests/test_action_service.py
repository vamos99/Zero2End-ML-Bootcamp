import pytest
from src.services import action_service
from src.services.action_service import simulate_impact

def test_simulate_impact_known_action():
    """Known actions expose an experiment outcome, not invented ROI."""
    action = "%15 İndirim Tanımla"
    api_response = simulate_impact(action)
    
    assert api_response["hypothesis"] == "Reactivation conversion rate"
    assert api_response["metric"] == "repeat_customer_rate_pct"
    assert api_response["status"] == "experiment_design_only"
    assert "control group" in api_response["evidence_needed"]
    assert "roi" not in api_response

def test_simulate_impact_unknown_action():
    """Test that unknown actions return default values."""
    action = "Unknown Action"
    api_response = simulate_impact(action)
    
    assert api_response["hypothesis"] == "Define before launch"
    assert api_response["metric"] == "define_primary_metric"
    assert api_response["status"] == "not_ready"


def test_get_recommendations_preserves_api_metadata(monkeypatch):
    response = {
        "recommendations": ["cama_mesa_banho"],
        "method": "popularity_fallback (User Unknown)",
        "item_type": "product_category",
    }

    class FakeClient:
        def get_recommendation_response(self, customer_id, n=5):
            assert customer_id == "USER_1"
            assert n == 5
            return response

    monkeypatch.setattr(action_service, "api_client", FakeClient())

    assert action_service.get_recommendations("USER_1") == response


def test_get_recommendations_handles_unavailable_api(monkeypatch):
    class FakeClient:
        def get_recommendation_response(self, customer_id, n=5):
            return None

    monkeypatch.setattr(action_service, "api_client", FakeClient())

    assert action_service.get_recommendations("USER_1") == {
        "error": "Recommendation API is unavailable or not configured."
    }
