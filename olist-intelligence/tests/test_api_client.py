"""Tests for dashboard API client configuration."""

from unittest.mock import MagicMock

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
