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

def test_predict_delivery_mock():
    # Test the mock endpoint
    response = client.post("/predict/delivery")
    assert response.status_code == 200
    assert "predicted_days" in response.json()

def test_predict_churn_mock():
    # Test the mock endpoint
    response = client.post("/predict/churn")
    assert response.status_code == 200
    assert "churn_probability" in response.json()
