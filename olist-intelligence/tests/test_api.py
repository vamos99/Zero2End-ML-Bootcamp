from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from src.app import app, get_db

client = TestClient(app)

# Helper to override DB dependency
def override_get_db():
    try:
        db = MagicMock()
        
        # Mocking the query result for /order/{id}/prediction
        mock_order_result = MagicMock()
        mock_order_result.fetchone.return_value = ("ORD-123", "CUST-999", 12.5, 10.0)
        
        # Mocking the query result for /customers/{id}/segment
        mock_customer_result = MagicMock()
        mock_customer_result.fetchone.return_value = ("USER-ABC", 120, 5, 500.50, 0, "Loyal")
        
        # Side effect to return different mocks based on query text
        def execute_side_effect(query, params):
            str_query = str(query)
            if "logistics_predictions" in str_query:
                return mock_order_result
            elif "customer_segments" in str_query:
                return mock_customer_result
            return MagicMock()
            
        db.execute.side_effect = execute_side_effect
        yield db
    finally:
        pass

# Apply override
app.dependency_overrides[get_db] = override_get_db

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome" in response.json()["message"]

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

from unittest.mock import patch

def test_predict_delivery_real():
    # Mock the loaded models in app.models
    with patch("src.app.models") as mock_models:
        # Setup Mock Model
        mock_logistics = MagicMock()
        mock_logistics.predict.return_value = [7.5] # Return list as model does
        mock_models.__getitem__.side_effect = lambda k: mock_logistics if k == "logistics" else None
        mock_models.__contains__.side_effect = lambda k: k == "logistics"
        
        payload = {
            "freight_value": 15.5,
            "price": 100.0,
            "product_weight_g": 500.0,
            "product_description_lenght": 100.0
        }
        
        response = client.post("/predict/delivery", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["predicted_days"] == 7.5
        assert data["risk_level"] == "Low"

def test_predict_churn_real():
    with patch("src.app.models") as mock_models:
        # Setup Mock Model
        mock_churn = MagicMock()
        mock_churn.predict.return_value = [1]
        mock_churn.predict_proba.return_value = [[0.2, 0.8]] # 80% True
        
        mock_models.__getitem__.side_effect = lambda k: mock_churn if k == "churn" else None
        mock_models.__contains__.side_effect = lambda k: k == "churn"
        
        payload = {
            "days_since_last_order": 10,
            "frequency": 5,
            "monetary": 1000
        }
        
        response = client.post("/predict/churn", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["churn_probability"] is not None
        assert "risk_level" in data
import numpy as np

def test_recommend_products():
    with patch("src.app.models") as mock_models:
        # Setup Mock Recommender Artifact
        mock_artifact = {
            "user_map": {"USER_1": 0},
            "reverse_product_map": {0: "PROD_A", 1: "PROD_B", 2: "PROD_C"},
            "matrix_reduced": np.array([[1.0, 0.1]]), # User 0 vector (2 dims)
            "product_components": np.array([
                [1.0, 0.0, 0.5], # Feature 1 weights for 3 products
                [0.0, 1.0, 0.5]  # Feature 2 weights for 3 products
            ])
        }
        # Math: User [1, 0.1]
        # Prod A: [1, 0] -> Score 1.0
        # Prod B: [0, 1] -> Score 0.1
        # Prod C: [0.5, 0.5] -> Score 0.55
        # Expected Order: A, C, B
        
        mock_models.__getitem__.side_effect = lambda k: mock_artifact if k == "recommender" else None
        mock_models.__contains__.side_effect = lambda k: k == "recommender"
        
        # Test Case 1: Known User
        payload = {"customer_id": "USER_1", "top_k": 2}
        response = client.post("/recommend", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["method"] == "personalized_svd"
        assert data["recommendations"] == ["PROD_A", "PROD_C"]
        
        # Test Case 2: Unknown User (Cold Start)
        payload = {"customer_id": "UNKNOWN_USER", "top_k": 5}
        response = client.post("/recommend", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "popularity_fallback" in data["method"]
