import pandas as pd
from src.database import repository

def get_daily_pulse(start_date, end_date):
    """Aggregates key metrics for the Home Page."""
    total_orders = repository.get_total_orders(start_date, end_date)
    risk_logistics = repository.get_logistics_risk_count(start_date, end_date)
    risk_churn = repository.get_churn_risk_count()
    revenue_metrics = repository.get_revenue_metrics(start_date, end_date)
    quality_metrics = repository.get_review_delivery_quality(start_date, end_date)
    
    return {
        "total_orders": total_orders,
        "risk_logistics": risk_logistics,
        "risk_churn": risk_churn,
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
    
    segment_map = {
        0: "💎 Sadık Müşteriler (Loyal)",
        1: "🌱 Yeni Potansiyeller (New)",
        2: "⚠️ Kayıp Riski (At Risk)",
        3: "🏆 Şampiyonlar (Champions)",
        4: "💤 Uyuyanlar (Hibernating)"
    }
    
    df_growth["Segment Adı"] = df_growth["Cluster"].map(segment_map).fillna("Diğer")
    return df_growth

def get_target_audience_data(segment_name):
    """Prepares data for Target Audience export."""
    cluster_map_reverse = {
        "💎 Sadık Müşteriler": 0,
        "🌱 Yeni Potansiyeller": 1,
        "⚠️ Kayıp Riski": 2,
        "🏆 Şampiyonlar": 3,
        "💤 Uyuyanlar": 4
    }
    
    cluster_id = cluster_map_reverse.get(segment_name) if segment_name != "Tümü" else None
    df_target = repository.get_target_audience(cluster_id)
    
    # Masking Logic
    if not df_target.empty:
        df_target['Müşteri ID'] = df_target['customer_unique_id'].apply(lambda x: f"USER-{x[:5]}***")
        df_target = df_target.drop(columns=['customer_unique_id'])
        
    return df_target
