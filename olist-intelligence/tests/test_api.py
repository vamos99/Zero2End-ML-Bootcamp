from fastapi.testclient import TestClient
from unittest.mock import MagicMock
import asyncio

import numpy as np
import pytest
from fastapi import HTTPException
from unittest.mock import patch

from src.app import app, get_db

client = TestClient(app)
API_HEADERS = {"X-API-KEY": "test-key"}

def override_get_db():
    try:
        db = MagicMock()
        mock_order_result = MagicMock()
        mock_order_result.fetchone.return_value = ("ORD-123", "CUST-999", 12.5, 10.0)
        mock_customer_result = MagicMock()
        mock_customer_result.fetchone.return_value = ("USER-ABC", 120, 5, 500.50, 0, "Loyal")
        mock_segment_summary_result = MagicMock()
        mock_segment_summary_result.fetchall.return_value = [("Loyal", 3), ("Dormant", 2)]
        
        def execute_side_effect(query, params=None):
            str_query = str(query)
            if "logistics_predictions" in str_query:
                return mock_order_result
            if "customer_segments" in str_query and "GROUP BY" in str_query:
                return mock_segment_summary_result
            if "customer_segments" in str_query:
                return mock_customer_result
            return MagicMock()
            
        db.execute.side_effect = execute_side_effect
        yield db
    finally:
        pass

app.dependency_overrides[get_db] = override_get_db

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome" in response.json()["message"]

def test_health_check_reports_readiness_without_secrets():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "database_configured" in data
    assert "api_key_configured" in data
    assert "loaded_models" in data

def test_api_key_verification_requires_config(monkeypatch):
    import src.app as api_app
    monkeypatch.setattr(api_app, "API_KEY", None)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(api_app.verify_api_key("any-value"))
    assert exc_info.value.status_code == 503


def test_protected_inference_endpoint_rejects_missing_api_key(monkeypatch):
    import src.app as api_app
    monkeypatch.setattr(api_app, "API_KEY", "test-key")
    response = client.post(
        "/predict/churn",
        json={"days_since_last_order": 10, "frequency": 5, "monetary": 1000},
    )
    assert response.status_code == 401


def test_get_order_prediction():
    response = client.get("/orders/ORD-123/prediction")
    assert response.status_code == 200
    data = response.json()
    assert data["order_id"] == "ORD-123"
    assert data["predicted_delivery_days"] == 12.5

def test_get_customer_segment():
    response = client.get("/customers/USER-ABC/segment")
    assert response.status_code == 200
    data = response.json()
    assert data["customer_unique_id"] == "USER-ABC"
    assert data["segment"] == "Loyal"
    assert data["recency"] == 120


def test_get_segment_distribution():
    response = client.get("/segments")
    assert response.status_code == 200
    data = response.json()
    assert data["segments"] == [
        {"segment": "Loyal", "customer_count": 3},
        {"segment": "Dormant", "customer_count": 2},
    ]
    assert data["total_customers"] == 5


def test_predict_delivery_real(monkeypatch):
    import src.app as api_app
    monkeypatch.setattr(api_app, "API_KEY", "test-key")
    with patch("src.app.models") as mock_models:
        mock_logistics = MagicMock()
        mock_logistics.predict.return_value = [7.5]
        mock_models.__getitem__.side_effect = lambda k: mock_logistics if k == "logistics" else None
        mock_models.__contains__.side_effect = lambda k: k == "logistics"
        payload = {
            "freight_value": 15.5,
            "price": 100.0,
            "product_weight_g": 500.0,
            "product_description_lenght": 100.0
        }
        response = client.post("/predict/delivery", json=payload, headers=API_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert data["predicted_days"] == 7.5
        assert data["risk_level"] == "Low"

def test_predict_churn_real(monkeypatch):
    import src.app as api_app
    monkeypatch.setattr(api_app, "API_KEY", "test-key")
    with patch("src.app.models") as mock_models:
        mock_churn = MagicMock()
        mock_churn.predict.return_value = [1]
        mock_churn.predict_proba.return_value = [[0.2, 0.8]]
        mock_models.__getitem__.side_effect = lambda k: mock_churn if k == "churn" else None
        mock_models.__contains__.side_effect = lambda k: k == "churn"
        payload = {
            "days_since_last_order": 10,
            "frequency": 5,
            "monetary": 1000
        }
        response = client.post("/predict/churn", json=payload, headers=API_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert data["churn_probability"] is not None
        assert "risk_level" in data


def test_recommend_products(monkeypatch):
    import src.app as api_app
    monkeypatch.setattr(api_app, "API_KEY", "test-key")
    with patch("src.app.models") as mock_models:
        mock_artifact = {
            "user_map": {"USER_1": 0},
            "reverse_product_map": {0: "PROD_A", 1: "PROD_B", 2: "PROD_C"},
            "matrix_reduced": np.array([[1.0, 0.1]]),
            "product_components": np.array([
                [1.0, 0.0, 0.5],
                [0.0, 1.0, 0.5]
            ])
        }
        mock_models.__getitem__.side_effect = lambda k: mock_artifact if k == "recommender" else None
        mock_models.__contains__.side_effect = lambda k: k == "recommender"
        payload = {"customer_id": "USER_1", "top_k": 2}
        response = client.post("/recommend", json=payload, headers=API_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert data["method"] == "personalized_svd"
        assert data["recommendations"] == ["PROD_A", "PROD_C"]
        payload = {"customer_id": "UNKNOWN_USER", "top_k": 5}
        response = client.post("/recommend", json=payload, headers=API_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert "popularity_fallback" in data["method"]
