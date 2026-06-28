import pandas as pd
from src.database import repository


def build_impact_scenario_summary(source_baselines, late_reduction_pct=10, repeat_uplift_pp=1.0):
    """Build lightweight source-baseline and planning scenario metrics."""
    delivery = source_baselines.get("delivery", {})
    repeat = source_baselines.get("repeat_purchase", {})

    delivered_orders = delivery.get("delivered_orders", 0)
    late_orders = delivery.get("late_orders", 0)
    late_rate = delivery.get("late_delivery_rate_pct", 0.0)
    avg_late_days = delivery.get("avg_days_late_when_late", 0.0)
    prevented_late_orders = late_orders * late_reduction_pct / 100
    projected_late_rate = (
        (late_orders - prevented_late_orders) / delivered_orders * 100
        if delivered_orders
        else 0.0
    )

    unique_customers = repeat.get("unique_customers", 0)
    repeat_rate = repeat.get("repeat_customer_rate_pct", 0.0)
    additional_repeat_customers = unique_customers * repeat_uplift_pp / 100

    return {
        "source_baselines": source_baselines,
        "delivery_scenario": {
            "assumption": f"{late_reduction_pct}% fewer late deliveries",
            "baseline_late_rate_pct": late_rate,
            "projected_late_rate_pct": projected_late_rate,
            "late_rate_delta_pp": projected_late_rate - late_rate,
            "prevented_late_orders": prevented_late_orders,
            "potential_late_days_avoided": prevented_late_orders * avg_late_days,
        },
        "repeat_purchase_scenario": {
            "assumption": f"+{repeat_uplift_pp:.1f} pp repeat-customer uplift",
            "baseline_repeat_rate_pct": repeat_rate,
            "projected_repeat_rate_pct": min(100.0, repeat_rate + repeat_uplift_pp),
            "additional_repeat_customers": additional_repeat_customers,
        },
        "boundary": "Scenario targets are assumptions for future experiments, not measured impact.",
    }

def get_daily_pulse(start_date, end_date):
    """Aggregates key metrics for the Home Page."""
    total_orders = repository.get_total_orders(start_date, end_date)
    risk_logistics = repository.get_logistics_risk_count(start_date, end_date)
    risk_churn = repository.get_churn_risk_count()
    revenue_metrics = repository.get_revenue_metrics(start_date, end_date)
    quality_metrics = repository.get_review_delivery_quality(start_date, end_date)
    generated_outputs = repository.get_generated_output_status()
    
    return {
        "total_orders": total_orders,
        "risk_logistics": risk_logistics,
        "risk_churn": risk_churn,
        "generated_outputs": generated_outputs,
        **revenue_metrics,
        **quality_metrics,
    }

def get_executive_dashboard_data(start_date, end_date):
    """Prepares summary charts for the executive home page."""
    revenue_by_state = repository.get_revenue_by_state(start_date, end_date)
    review_delivery_matrix = repository.get_review_delivery_matrix(start_date, end_date)
    payment_mix = repository.get_payment_mix_summary(start_date, end_date)
    cohort_retention = repository.get_cohort_retention_matrix(start_date, end_date)
    seller_sla_watchlist = repository.get_seller_sla_watchlist()
    impact_summary = build_impact_scenario_summary(repository.get_source_business_baselines())

    if not seller_sla_watchlist.empty and "seller_id" in seller_sla_watchlist.columns:
        seller_sla_watchlist = seller_sla_watchlist.copy()
        seller_sla_watchlist["seller_label"] = seller_sla_watchlist["seller_id"].apply(
            lambda value: f"Seller {str(value)[:8]}..."
        )

    return {
        "revenue_by_state": revenue_by_state,
        "review_delivery_matrix": review_delivery_matrix,
        "payment_mix": payment_mix,
        "cohort_retention": cohort_retention,
        "seller_sla_watchlist": seller_sla_watchlist,
        "impact_summary": impact_summary,
    }

def get_logistics_data(start_date, end_date):
    """Prepares data for Logistics View."""
    risk_count = repository.get_logistics_risk_count(start_date, end_date)
    metrics = repository.get_logistics_metrics(start_date, end_date)
    df_details = repository.get_logistics_details(start_date, end_date)
    
    # Masking Logic
    if not df_details.empty:
        df_details['Müşteri Kodu'] = df_details['customer_id'].apply(lambda x: f"CUST-{x[:5]}...")
        df_details = df_details.drop(columns=['customer_id'])
        
    return risk_count, metrics, df_details

def get_segmentation_data():
    """Prepares data for Growth View."""
    df_growth = repository.get_customer_segments_stats()
    if not df_growth.empty:
        df_growth["Segment Adı"] = df_growth["Segment"].fillna("Unlabeled")
    return df_growth

def get_target_audience_data(segment_name):
    """Prepares data for Target Audience export."""
    selected_segment = None if segment_name == "Tümü" else segment_name
    df_target = repository.get_target_audience(selected_segment)
    
    # Masking Logic
    if not df_target.empty:
        df_target['Müşteri ID'] = df_target['customer_unique_id'].apply(lambda x: f"USER-{x[:5]}***")
        df_target = df_target.drop(columns=['customer_unique_id'])
        
    return df_target
