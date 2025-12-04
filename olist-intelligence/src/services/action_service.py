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
