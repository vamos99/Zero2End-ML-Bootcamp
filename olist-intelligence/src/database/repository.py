import pandas as pd
from sqlalchemy import inspect, text
from src.database.db_client import get_db_connection
from src.database import (
    action_repository,
    customer_repository,
    executive_repository,
    logistics_repository,
    ranking_repository,
)

engine = get_db_connection()


def get_generated_output_status():
    """Report whether notebook/model-generated dashboard tables are available."""
    table_names = set(inspect(engine).get_table_names())
    return {
        "logistics_predictions": "logistics_predictions" in table_names,
        "customer_segments": "customer_segments" in table_names,
    }


def get_total_orders(start_date, end_date):
    query = text("""
    SELECT COUNT(DISTINCT order_id)
    FROM orders
    WHERE DATE(order_purchase_timestamp) BETWEEN DATE(:start_date) AND DATE(:end_date)
    """)
    try:
        return int(
            pd.read_sql(
                query,
                engine,
                params={"start_date": start_date, "end_date": end_date},
            ).iloc[0, 0]
        )
    except Exception:
        return 0


def get_date_range():
    query = "SELECT MIN(order_purchase_timestamp), MAX(order_purchase_timestamp) FROM orders"
    # This standard SQL works on both SQLite and Postgres
    result = pd.read_sql(text(query), engine)
    return result.iloc[0, 0], result.iloc[0, 1]


def get_revenue_metrics(start_date, end_date):
    """Backward-compatible facade for executive revenue metrics."""
    return executive_repository.get_revenue_metrics(start_date, end_date)


def get_review_delivery_quality(start_date, end_date):
    """Backward-compatible facade for review and delivery quality metrics."""
    return executive_repository.get_review_delivery_quality(start_date, end_date)


def get_source_business_baselines():
    """Backward-compatible facade for source baseline scenario inputs."""
    return executive_repository.get_source_business_baselines()


def get_revenue_by_state(start_date, end_date, limit=12):
    """Backward-compatible facade for customer-state revenue rankings."""
    return executive_repository.get_revenue_by_state(start_date, end_date, limit)


def get_review_delivery_matrix(start_date, end_date):
    """Backward-compatible facade for review-score delivery matrix rows."""
    return executive_repository.get_review_delivery_matrix(start_date, end_date)


def get_payment_mix_summary(start_date, end_date, limit=6):
    """Backward-compatible facade for payment mix mart summaries."""
    return executive_repository.get_payment_mix_summary(start_date, end_date, limit)


def get_cohort_retention_matrix(
    start_date,
    end_date,
    max_cohorts=8,
    max_months=6,
    min_cohort_size=100,
):
    """Backward-compatible facade for cohort retention matrix rows."""
    return executive_repository.get_cohort_retention_matrix(
        start_date,
        end_date,
        max_cohorts,
        max_months,
        min_cohort_size,
    )


def get_seller_sla_watchlist(limit=10, min_orders=20):
    """Backward-compatible facade for seller SLA watchlist rows."""
    return executive_repository.get_seller_sla_watchlist(limit, min_orders)


def get_category_performance_summary(limit=10, min_orders=100):
    """Backward-compatible facade for category performance mart rows."""
    return executive_repository.get_category_performance_summary(limit, min_orders)


def get_location_service_levels(limit=12, min_orders=100):
    """Backward-compatible facade for location service-level mart rows."""
    return executive_repository.get_location_service_levels(limit, min_orders)


def get_logistics_metrics(start_date, end_date):
    """Backward-compatible facade for logistics metrics."""
    return logistics_repository.get_logistics_metrics(start_date, end_date)


def get_logistics_risk_count(start_date, end_date):
    """Backward-compatible facade for logistics risk counts."""
    return logistics_repository.get_logistics_risk_count(start_date, end_date)


def get_logistics_details(start_date, end_date, limit=10):
    """Backward-compatible facade for logistics detail rows."""
    return logistics_repository.get_logistics_details(start_date, end_date, limit)


def get_churn_risk_count():
    """Backward-compatible facade for the relative At Risk segment count."""
    return customer_repository.get_churn_risk_count()


def get_customer_segments_stats():
    """Backward-compatible facade for generated segment summaries."""
    return customer_repository.get_customer_segments_stats()


def get_target_audience(segment_name=None, limit=500):
    """Backward-compatible facade for target-audience exports."""
    return customer_repository.get_target_audience(segment_name, limit)


def log_action_to_db(action_type, description, impact_value):
    """Backward-compatible facade for action logging."""
    return action_repository.log_action_to_db(action_type, description, impact_value)


def get_recent_actions(limit=5):
    """Backward-compatible facade for recent actions."""
    return action_repository.get_recent_actions(limit)


def init_bi_tables():
    """Backward-compatible facade for action table initialization."""
    return action_repository.init_bi_tables()


def get_top_products(limit=20, start_date=None, end_date=None):
    """Backward-compatible facade for product category rankings."""
    return ranking_repository.get_top_products(limit, start_date, end_date)


def get_top_sellers(limit=20, start_date=None, end_date=None):
    """Backward-compatible facade for seller rankings."""
    return ranking_repository.get_top_sellers(limit, start_date, end_date)


def get_category_performance(start_date=None, end_date=None):
    """Backward-compatible facade for category performance."""
    return ranking_repository.get_category_performance(start_date, end_date)


def get_random_customer_id():
    """Backward-compatible facade for dashboard customer sampling."""
    return customer_repository.get_random_customer_id()
