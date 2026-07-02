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


def build_dashboard_outcome_scorecard(
    impact_summary,
    payment_mix=None,
    cohort_retention=None,
    seller_sla_watchlist=None,
    category_performance=None,
    location_service_levels=None,
):
    """Build lightweight dashboard rows that separate baselines from impact."""
    source_baselines = impact_summary.get("source_baselines", {})
    delivery = source_baselines.get("delivery", {})
    repeat = source_baselines.get("repeat_purchase", {})
    delivery_scenario = impact_summary.get("delivery_scenario", {})
    repeat_scenario = impact_summary.get("repeat_purchase_scenario", {})
    repeat_delta_pp = (
        repeat_scenario.get("projected_repeat_rate_pct", 0.0)
        - repeat_scenario.get("baseline_repeat_rate_pct", 0.0)
    )

    payment_methods = len(payment_mix) if payment_mix is not None else 0
    cohort_rows = len(cohort_retention) if cohort_retention is not None else 0
    seller_rows = len(seller_sla_watchlist) if seller_sla_watchlist is not None else 0
    category_rows = len(category_performance) if category_performance is not None else 0
    location_rows = len(location_service_levels) if location_service_levels is not None else 0

    return [
        {
            "area": "Actual delivery operation",
            "baseline": f"{delivery.get('late_delivery_rate_pct', 0.0):.2f}% late rate",
            "current_or_target": "No post-intervention delivery period",
            "measured_change": "No actual delivery-time improvement measured",
            "status": "Source baseline only",
        },
        {
            "area": "Delivery scenario target",
            "baseline": f"{delivery_scenario.get('baseline_late_rate_pct', 0.0):.2f}% late rate",
            "current_or_target": f"{delivery_scenario.get('projected_late_rate_pct', 0.0):.2f}% late rate",
            "measured_change": (
                f"{delivery_scenario.get('late_rate_delta_pp', 0.0):.2f} pp target; "
                f"{delivery_scenario.get('prevented_late_orders', 0.0):,.0f} late orders if validated"
            ),
            "status": "Future experiment target",
        },
        {
            "area": "Repeat purchase / churn",
            "baseline": (
                f"{repeat.get('repeat_customer_rate_pct', 0.0):.2f}% repeat; "
                f"{repeat.get('one_time_customer_rate_pct', 0.0):.2f}% one-time"
            ),
            "current_or_target": "No measured campaign result",
            "measured_change": "No churn or retention uplift measured",
            "status": "Use cohort retention before impact claims",
        },
        {
            "area": "Repeat-purchase scenario target",
            "baseline": f"{repeat_scenario.get('baseline_repeat_rate_pct', 0.0):.2f}% repeat",
            "current_or_target": f"{repeat_scenario.get('projected_repeat_rate_pct', 0.0):.2f}% repeat",
            "measured_change": (
                f"+{repeat_delta_pp:.1f} pp target; "
                f"{repeat_scenario.get('additional_repeat_customers', 0.0):,.0f} repeat customers if validated"
            ),
            "status": "Future experiment target",
        },
        {
            "area": "Executive analytics coverage",
            "baseline": "Raw Olist tables",
            "current_or_target": (
                f"{payment_methods} payment methods; {cohort_rows} cohort rows; "
                f"{seller_rows} seller watchlist rows; {category_rows} category rows; "
                f"{location_rows} location lanes"
            ),
            "measured_change": "Dashboard evidence coverage improved, not business outcome",
            "status": "SQL mart coverage",
        },
    ]


def build_dashboard_answer_cards(impact_summary, outcome_scorecard):
    """Build dashboard-safe baseline/result/delta rows for executive readers."""
    delivery_scenario = impact_summary.get("delivery_scenario", {})
    repeat_scenario = impact_summary.get("repeat_purchase_scenario", {})
    rows_by_area = {row.get("area"): row for row in outcome_scorecard}

    delivery_actual = rows_by_area.get("Actual delivery operation", {})
    churn = rows_by_area.get("Repeat purchase / churn", {})
    analytics = rows_by_area.get("Executive analytics coverage", {})

    return [
        {
            "area": "Delivery operation",
            "result_type": "source_baseline",
            "baseline": delivery_actual.get("baseline", "0.00% late rate"),
            "current_or_target": delivery_actual.get(
                "current_or_target",
                "No post-intervention delivery period",
            ),
            "delta_or_change": delivery_actual.get(
                "measured_change",
                "No actual delivery-time improvement measured",
            ),
            "boundary": "Delivery speed has not been proven faster from this dataset.",
        },
        {
            "area": "Delivery scenario",
            "result_type": "planning_scenario",
            "baseline": f"{delivery_scenario.get('baseline_late_rate_pct', 0.0):.2f}% late rate",
            "current_or_target": f"{delivery_scenario.get('projected_late_rate_pct', 0.0):.2f}% late rate",
            "delta_or_change": (
                f"{delivery_scenario.get('late_rate_delta_pp', 0.0):.2f} pp target; "
                f"{delivery_scenario.get('prevented_late_orders', 0.0):,.0f} fewer late orders; "
                f"{delivery_scenario.get('potential_late_days_avoided', 0.0):,.0f} potential late-days"
            ),
            "boundary": "Scenario target only; validate before calling it impact.",
        },
        {
            "area": "Repeat purchase / churn",
            "result_type": "source_baseline",
            "baseline": churn.get("baseline", "0.00% repeat; 0.00% one-time"),
            "current_or_target": churn.get("current_or_target", "No measured campaign result"),
            "delta_or_change": churn.get("measured_change", "No churn or retention uplift measured"),
            "boundary": "Use cohort retention and experiments before claiming churn reduction.",
        },
        {
            "area": "Repeat-purchase scenario",
            "result_type": "planning_scenario",
            "baseline": f"{repeat_scenario.get('baseline_repeat_rate_pct', 0.0):.2f}% repeat",
            "current_or_target": f"{repeat_scenario.get('projected_repeat_rate_pct', 0.0):.2f}% repeat",
            "delta_or_change": (
                f"+{repeat_scenario.get('projected_repeat_rate_pct', 0.0) - repeat_scenario.get('baseline_repeat_rate_pct', 0.0):.1f} pp target; "
                f"{repeat_scenario.get('additional_repeat_customers', 0.0):,.0f} additional repeat customers"
            ),
            "boundary": "Campaign target only; not measured churn improvement.",
        },
        {
            "area": "Analytics coverage",
            "result_type": "analytics_signal",
            "baseline": analytics.get("baseline", "Raw Olist tables"),
            "current_or_target": analytics.get("current_or_target", "No dashboard marts available"),
            "delta_or_change": analytics.get(
                "measured_change",
                "Dashboard evidence coverage improved, not business outcome",
            ),
            "boundary": "Coverage helps explain business state; it is not intervention impact.",
        },
    ]


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
    seller_risk_scorecard = repository.get_seller_risk_scorecard()
    category_performance = repository.get_category_performance_summary()
    location_service_levels = repository.get_location_service_levels()
    impact_summary = build_impact_scenario_summary(repository.get_source_business_baselines())

    if not seller_sla_watchlist.empty and "seller_id" in seller_sla_watchlist.columns:
        seller_sla_watchlist = seller_sla_watchlist.copy()
        seller_sla_watchlist["seller_label"] = seller_sla_watchlist["seller_id"].apply(
            lambda value: f"Seller {str(value)[:8]}..."
        )
    if not seller_risk_scorecard.empty and "seller_id" in seller_risk_scorecard.columns:
        seller_risk_scorecard = seller_risk_scorecard.copy()
        seller_risk_scorecard["seller_label"] = seller_risk_scorecard["seller_id"].apply(
            lambda value: f"Seller {str(value)[:8]}..."
        )
    outcome_scorecard = build_dashboard_outcome_scorecard(
        impact_summary,
        payment_mix=payment_mix,
        cohort_retention=cohort_retention,
        seller_sla_watchlist=seller_sla_watchlist,
        category_performance=category_performance,
        location_service_levels=location_service_levels,
    )
    dashboard_answer_cards = build_dashboard_answer_cards(impact_summary, outcome_scorecard)

    return {
        "revenue_by_state": revenue_by_state,
        "review_delivery_matrix": review_delivery_matrix,
        "payment_mix": payment_mix,
        "cohort_retention": cohort_retention,
        "seller_sla_watchlist": seller_sla_watchlist,
        "seller_risk_scorecard": seller_risk_scorecard,
        "category_performance": category_performance,
        "location_service_levels": location_service_levels,
        "impact_summary": impact_summary,
        "outcome_scorecard": outcome_scorecard,
        "dashboard_answer_cards": dashboard_answer_cards,
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
