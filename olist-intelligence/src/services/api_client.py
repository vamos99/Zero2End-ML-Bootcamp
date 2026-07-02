"""API Client for Dashboard to communicate with FastAPI backend."""
import logging
import os
from typing import Dict, List, Optional

import requests


logger = logging.getLogger(__name__)


class APIClient:
    """Client for interacting with Olist Intelligence API."""
    
    def __init__(self, base_url: str = None, api_key: str = None):
        # Prefer 127.0.0.1 for local env to avoid MacOS localhost issues
        default_url = "http://127.0.0.1:8000"
        self.base_url = base_url or os.getenv("API_URL", default_url)
        self.api_key = api_key or os.getenv("API_KEY")
        self.headers = {"X-API-KEY": self.api_key} if self.api_key else {}
        self.last_error: Optional[Dict] = None

    @staticmethod
    def _extract_error_detail(response):
        try:
            body = response.json()
        except ValueError:
            return response.text or response.reason

        detail = body.get("detail")
        if isinstance(detail, (dict, list, str)):
            return detail
        return str(detail or body)
    
    def _handle_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Generic request handler with detailed error logging."""
        self.last_error = None
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.warning("API request failed [%s %s]: %s", method, endpoint, e)
            response = getattr(e, 'response', None)
            if response is not None:
                logger.debug("API response body [%s %s]: %s", method, endpoint, response.text)
                self.last_error = {
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "detail": self._extract_error_detail(response),
                }
            else:
                self.last_error = {
                    "endpoint": endpoint,
                    "status_code": None,
                    "detail": str(e),
                }
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
    
    def predict_repeat_purchase_risk(
        self,
        days_since: int,
        frequency: int,
        monetary: float,
    ) -> Optional[Dict]:
        """Predict repeat-purchase risk using the canonical API endpoint."""
        return self._handle_request(
            "POST",
            "/predict/repeat-purchase-risk",
            json={
                "days_since_last_order": days_since,
                "frequency": frequency,
                "monetary": monetary
            },
            timeout=5
        )

    def predict_churn(self, days_since: int, frequency: int, monetary: float) -> Optional[Dict]:
        """Legacy alias kept for older dashboard/API callers."""
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
    
    def get_recommendation_response(self, customer_id: str, n: int = 5) -> Optional[Dict]:
        """Get the full recommendation API response including method metadata."""
        return self._handle_request(
            "POST",
            "/recommend",
            json={"customer_id": customer_id, "top_k": n},
            timeout=5
        )

    def get_recommendations(self, customer_id: str, n: int = 5) -> Optional[List]:
        """Get product recommendations for a customer."""
        result = self.get_recommendation_response(customer_id, n=n)
        return result.get("recommendations", []) if result else []
    
    def get_segments(self) -> Optional[Dict]:
        """Get customer segment distribution."""
        return self._handle_request("GET", "/segments", timeout=5)

    def get_readiness(self) -> Optional[Dict]:
        """Get API readiness details without requiring an API key."""
        return self._handle_request("GET", "/ready", timeout=2)
    
    def health_check(self) -> bool:
        """Check if API is available."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=2)
            return response.status_code == 200
        except requests.RequestException:
            return False


# Singleton instance for dashboard use
api_client = APIClient()
