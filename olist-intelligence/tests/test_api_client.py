"""Tests for dashboard API client configuration."""

from unittest.mock import MagicMock

import requests

from src.services.api_client import APIClient


def test_api_client_omits_api_key_header_when_env_missing(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)

    client = APIClient(base_url="http://example.test")

    assert client.api_key is None
    assert client.headers == {}


def test_api_client_uses_explicit_api_key():
    client = APIClient(base_url="http://example.test", api_key="test-key")

    assert client.headers == {"X-API-KEY": "test-key"}


def test_get_recommendations_uses_api_schema_payload(monkeypatch):
    mock_response = MagicMock()
    mock_response.json.return_value = {"recommendations": ["PROD_A", "PROD_B"]}
    mock_response.raise_for_status.return_value = None

    request_mock = MagicMock(return_value=mock_response)
    monkeypatch.setattr("src.services.api_client.requests.request", request_mock)

    client = APIClient(base_url="http://example.test", api_key="test-key")
    result = client.get_recommendations("USER_1", n=2)

    assert result == ["PROD_A", "PROD_B"]
    request_mock.assert_called_once_with(
        "POST",
        "http://example.test/recommend",
        headers={"X-API-KEY": "test-key"},
        json={"customer_id": "USER_1", "top_k": 2},
        timeout=5,
    )


def test_get_recommendation_response_preserves_metadata(monkeypatch):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "recommendations": ["cama_mesa_banho"],
        "method": "popularity_fallback (User Unknown)",
        "item_type": "product_category",
    }
    mock_response.raise_for_status.return_value = None

    monkeypatch.setattr("src.services.api_client.requests.request", MagicMock(return_value=mock_response))

    client = APIClient(base_url="http://example.test", api_key="test-key")
    result = client.get_recommendation_response("USER_1", n=1)

    assert result["recommendations"] == ["cama_mesa_banho"]
    assert result["method"] == "popularity_fallback (User Unknown)"
    assert result["item_type"] == "product_category"


def test_api_client_stores_structured_error_detail(monkeypatch):
    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_response.json.return_value = {"detail": "Model not loaded"}
    mock_response.__bool__.return_value = False
    mock_response.raise_for_status.side_effect = requests.HTTPError(response=mock_response)

    monkeypatch.setattr("src.services.api_client.requests.request", MagicMock(return_value=mock_response))

    client = APIClient(base_url="http://example.test", api_key="test-key")
    result = client.predict_churn(days_since=30, frequency=2, monetary=250)

    assert result is None
    assert client.last_error == {
        "endpoint": "/predict/churn",
        "status_code": 503,
        "detail": "Model not loaded",
    }


def test_get_readiness_uses_public_ready_endpoint(monkeypatch):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "status": "ready",
        "generated_tables": {"logistics_predictions": True},
        "loaded_models": ["logistics"],
    }
    mock_response.raise_for_status.return_value = None

    request_mock = MagicMock(return_value=mock_response)
    monkeypatch.setattr("src.services.api_client.requests.request", request_mock)

    client = APIClient(base_url="http://example.test", api_key="test-key")
    result = client.get_readiness()

    assert result["loaded_models"] == ["logistics"]
    request_mock.assert_called_once_with(
        "GET",
        "http://example.test/ready",
        headers={"X-API-KEY": "test-key"},
        timeout=2,
    )
