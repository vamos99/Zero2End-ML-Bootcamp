"""API Client for Dashboard to communicate with FastAPI backend."""
import os
import requests
from typing import Dict, List, Optional


class APIClient:
    """Client for interacting with Olist Intelligence API."""
    
    def __init__(self, base_url: str = None, api_key: str = None):
        # Prefer 127.0.0.1 for local env to avoid MacOS localhost issues
        default_url = "http://127.0.0.1:8000"
        self.base_url = base_url or os.getenv("API_URL", default_url)
        self.api_key = api_key or os.getenv("API_KEY", "olist-dev-key-2024")
        self.headers = {"X-API-KEY": self.api_key}
    
    def _handle_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Generic request handler with detailed error logging."""
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"❌ API Error [{method} {endpoint}]: {e}")
            if response := getattr(e, 'response', None):
                print(f"📜 Detailed Response: {response.text}")
            return None

    def predict_delivery(self, freight: float, price: float, weight: float,
                         desc_length: int, distance: float, same_state: int,
                         seller_rating: float) -> Optional[Dict]:
        """Predict delivery time for an order."""
        return self._handle_request(
            "POST", 
            "/predict/delivery",
            json={
                "freight_value": freight,
                "price": price,
                "product_weight_g": weight,
                "product_description_lenght": desc_length,
                "distance_km": distance,
                "same_state": same_state,
                "seller_avg_rating": seller_rating
            },
            timeout=5
        )
    
    def predict_churn(self, days_since: int, frequency: int, monetary: float) -> Optional[Dict]:
        """Predict churn probability for a customer."""
        return self._handle_request(
            "POST",
            "/predict/churn",
            json={
                "days_since_last_order": days_since,
                "frequency": frequency,
                "monetary": monetary
            },
            timeout=5
        )
    
    def get_recommendations(self, customer_id: str, n: int = 5) -> Optional[List]:
        """Get product recommendations for a customer."""
        result = self._handle_request(
            "POST",
            "/recommend",
            json={"customer_unique_id": customer_id, "n_recommendations": n},
            timeout=5
        )
        return result.get("recommendations", []) if result else []
    
    def get_segments(self) -> Optional[Dict]:
        """Get customer segment distribution."""
        return self._handle_request("GET", "/segments", timeout=5)
    
    def health_check(self) -> bool:
        """Check if API is available."""
        try:
            response = requests.get(f"{self.base_url}/", timeout=2)
            return response.status_code == 200
        except requests.RequestException:
            return False


# Singleton instance for dashboard use
api_client = APIClient()
