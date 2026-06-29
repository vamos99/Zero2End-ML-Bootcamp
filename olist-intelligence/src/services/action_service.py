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
        "%15 İndirim Tanımla": {
            "hypothesis": "Reactivation conversion rate",
            "metric": "repeat_customer_rate_pct",
            "baseline_source": "source repeat-purchase baseline and cohort retention",
            "evidence_needed": "holdout campaign comparing repeat purchase against a control group",
            "status": "experiment_design_only",
        },
        "Sadakat Puanı Yükle": {
            "hypothesis": "Repeat purchase rate",
            "metric": "repeat_customer_rate_pct",
            "baseline_source": "source repeat-purchase baseline",
            "evidence_needed": "pre/post or holdout test with customer-level repeat-purchase tracking",
            "status": "experiment_design_only",
        },
        "Müşteri Temsilcisi Arasın": {
            "hypothesis": "Retention uplift",
            "metric": "repeat_customer_rate_pct",
            "baseline_source": "At Risk segment size and cohort retention",
            "evidence_needed": "controlled outreach log with post-contact repeat purchase outcome",
            "status": "experiment_design_only",
        },
    }
    return impact_map.get(
        action_name,
        {
            "hypothesis": "Define before launch",
            "metric": "define_primary_metric",
            "baseline_source": "define baseline before launch",
            "evidence_needed": "define control group and post-action measurement window",
            "status": "not_ready",
        },
    )

def get_recommendations(customer_id: str):
    """Call the configured API client and preserve the dashboard response shape."""
    response = api_client.get_recommendation_response(customer_id, n=5)
    if response is None:
        return {"error": "Recommendation API is unavailable or not configured."}
    return response
