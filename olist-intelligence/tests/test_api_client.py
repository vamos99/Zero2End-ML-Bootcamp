"""Tests for dashboard API client configuration."""

from src.services.api_client import APIClient


def test_api_client_omits_api_key_header_when_env_missing(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)

    client = APIClient(base_url="http://example.test")

    assert client.api_key is None
    assert client.headers == {}


def test_api_client_uses_explicit_api_key():
    client = APIClient(base_url="http://example.test", api_key="test-key")

    assert client.headers == {"X-API-KEY": "test-key"}
