"""MLflow availability and local model fallback tests."""

from unittest.mock import MagicMock

import pytest

from src.ml import registry


def test_mlflow_connection_uses_short_timeout(monkeypatch):
    request = MagicMock()
    monkeypatch.setattr(registry.requests, "get", request)

    assert registry.check_mlflow_connection("http://localhost:5000")
    request.assert_called_once_with("http://localhost:5000/health", timeout=2)


def test_local_model_roundtrip_without_mlflow(tmp_path, monkeypatch):
    monkeypatch.setattr(registry, "MODELS_PATH", tmp_path)
    monkeypatch.setattr(registry, "mlflow", None)
    model = {"kind": "test-artifact", "version": 1}

    registry.save_model_locally(model, "example")
    loaded = registry.load_production_model("example")

    assert loaded == model


def test_missing_local_model_is_explicit(tmp_path, monkeypatch):
    monkeypatch.setattr(registry, "MODELS_PATH", tmp_path)
    monkeypatch.setattr(registry, "mlflow", None)

    with pytest.raises(FileNotFoundError, match="Model not found"):
        registry.load_production_model("missing")
