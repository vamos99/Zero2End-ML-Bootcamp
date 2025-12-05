from src.database import repository

def init_system():
    repository.init_bi_tables()

def execute_action(action_type, description, impact_value):
    repository.log_action_to_db(action_type, description, impact_value)

def get_recent_history():
    return repository.get_recent_actions()

def simulate_impact(action_name):
    impact_map = {
        "%15 İndirim Tanımla": {"cost": 5000, "saved": 120000, "roi": "%2400"},
        "Sadakat Puanı Yükle": {"cost": 2000, "saved": 80000, "roi": "%4000"},
        "Müşteri Temsilcisi Arasın": {"cost": 15000, "saved": 200000, "roi": "%1333"}
    }
    return impact_map.get(action_name, {"cost": 0, "saved": 0, "roi": "N/A"})

import requests
from src.config import API_URL

def get_recommendations(customer_id: str):
    """
    Call the API to get personalized product recommendations.
    """
    try:
        response = requests.post(f"{API_URL}/recommend", json={"customer_id": customer_id, "top_k": 5})
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"API Error: {response.status_code}"}
    except Exception as e:
        return {"error": f"Connection Error: {e}"}
