from src.database import repository
from src.services.api_client import api_client

def init_system():
    repository.init_bi_tables()

def execute_action(action_type, description, impact_value):
    repository.log_action_to_db(action_type, description, impact_value)

def get_recent_history():
    return repository.get_recent_actions()

def simulate_impact(action_name):
    impact_map = {
        "%15 İndirim Tanımla": {"hypothesis": "Reactivation conversion rate"},
        "Sadakat Puanı Yükle": {"hypothesis": "Repeat purchase rate"},
        "Müşteri Temsilcisi Arasın": {"hypothesis": "Retention uplift"},
    }
    return impact_map.get(action_name, {"hypothesis": "Define before launch"})

def get_recommendations(customer_id: str):
    """Call the configured API client and preserve the dashboard response shape."""
    recommendations = api_client.get_recommendations(customer_id, n=5)
    if recommendations is None:
        return {"error": "Recommendation API is unavailable or not configured."}
    return {"recommendations": recommendations}
