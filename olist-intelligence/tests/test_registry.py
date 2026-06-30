"""MLflow availability and local model fallback tests."""

from unittest.mock import MagicMock

import pytest
from requests.exceptions import Timeout

from src.ml import registry


def test_mlflow_connection_uses_short_timeout(monkeypatch):
    request = MagicMock()
    monkeypatch.setattr(registry.requests, "get", request)

    assert registry.check_mlflow_connection("http://localhost:5000")
    request.assert_called_once_with("http://localhost:5000/health", timeout=2)


def test_mlflow_connection_returns_false_on_timeout(monkeypatch):
    request = MagicMock(side_effect=Timeout)
    monkeypatch.setattr(registry.requests, "get", request)

    assert not registry.check_mlflow_connection("http://localhost:5000")


def test_get_mlflow_client_fails_fast_when_server_unreachable(monkeypatch):
    fake_mlflow = MagicMock()
    fake_client = MagicMock()
    monkeypatch.setattr(registry, "mlflow", fake_mlflow)
    monkeypatch.setattr(registry, "MlflowClient", fake_client)
    monkeypatch.setattr(registry, "check_mlflow_connection", lambda _uri: False)

    with pytest.raises(registry.ConnectionError, match="MLflow Server Unreachable"):
        registry.get_mlflow_client()

    fake_mlflow.set_tracking_uri.assert_not_called()
    fake_client.assert_not_called()


def test_local_model_roundtrip_without_mlflow(tmp_path, monkeypatch):
    monkeypatch.setattr(registry, "MODELS_PATH", tmp_path)
    monkeypatch.setattr(registry, "mlflow", None)
    model = {"kind": "test-artifact", "version": 1}

    registry.save_model_locally(model, "example")
    loaded = registry.load_production_model("example")

    assert loaded == model


def test_register_model_saves_local_fallback_without_mlflow(tmp_path, monkeypatch):
    monkeypatch.setattr(registry, "MODELS_PATH", tmp_path / "models")
    monkeypatch.setattr(registry, "mlflow", None)
    model = {"kind": "fallback-artifact"}

    version = registry.register_model(model, "fallback", metrics={"mae": 1.2})

    assert version is None
    assert (tmp_path / "models" / "fallback_model.pkl").exists()
    assert registry.load_production_model("fallback") == model


def test_load_production_model_uses_local_when_mlflow_unreachable(tmp_path, monkeypatch):
    monkeypatch.setattr(registry, "MODELS_PATH", tmp_path)
    model = {"kind": "local-artifact"}
    registry.save_model_locally(model, "example")

    monkeypatch.setattr(registry, "mlflow", MagicMock())
    monkeypatch.setattr(
        registry,
        "get_mlflow_client",
        MagicMock(side_effect=registry.ConnectionError("MLflow Server Unreachable")),
    )

    loaded = registry.load_production_model("example")

    assert loaded == model


def test_missing_local_model_is_explicit(tmp_path, monkeypatch):
    monkeypatch.setattr(registry, "MODELS_PATH", tmp_path)
    monkeypatch.setattr(registry, "mlflow", None)

    with pytest.raises(FileNotFoundError, match="Model not found"):
        registry.load_production_model("missing")
