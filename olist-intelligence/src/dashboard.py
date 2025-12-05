import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.services import analytics_service, action_service
from src.views import home_view, logistics_view, customer_view, growth_view, ranking_view
from src.database import repository

# Page Config
st.set_page_config(
    page_title="Olist Intelligence Suite",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize System
action_service.init_system()

# Sidebar Navigation
st.sidebar.title("Olist Intelligence 🚀")
page = st.sidebar.radio("Modüller", ["Ana Sayfa", "📦 Operasyon Merkezi", "🤝 Müşteri Sadakati", "📊 Segmentasyon Analizi", "📈 Ranking & Trends"])

st.sidebar.markdown("---")
st.sidebar.subheader("📅 Tarih Aralığı")

# Dynamic Date Range
try:
    min_date, max_date = repository.get_date_range()
    # Fallback if DB is empty
    if pd.isnull(min_date):
        min_date = pd.to_datetime("2016-01-01")
        max_date = pd.to_datetime("2018-12-31")
except:
    min_date = pd.to_datetime("2016-01-01")
    max_date = pd.to_datetime("2018-12-31")

start_date = st.sidebar.date_input("Başlangıç", min_date, min_value=min_date, max_value=max_date)
end_date = st.sidebar.date_input("Bitiş", max_date, min_value=min_date, max_value=max_date)

st.sidebar.markdown("---")
st.sidebar.info("v3.0.0 - Full Audit Update")

# --- CONTROLLER LOGIC ---

if page == "Ana Sayfa":
    metrics = analytics_service.get_daily_pulse(start_date, end_date)
    home_view.render_home_view(metrics)

elif page == "📦 Operasyon Merkezi":
    risk_count, metrics, df_details = analytics_service.get_logistics_data(start_date, end_date)
    logistics_view.render_logistics_view(risk_count, metrics, df_details)

elif page == "🤝 Müşteri Sadakati":
    # Churn risk is currently a snapshot, passing total count
    risk_churn = analytics_service.get_daily_pulse(start_date, end_date)["risk_churn"]
    customer_view.render_customer_view(risk_churn)

elif page == "📊 Segmentasyon Analizi":
    df_growth = analytics_service.get_segmentation_data()
    growth_view.render_growth_view(df_growth)

elif page == "📈 Ranking & Trends":
    ranking_view.render_ranking_view()

# --- ACTION LOGS SIDEBAR ---
st.sidebar.markdown("---")
st.sidebar.subheader("📜 Son İşlemler")
try:
    logs = action_service.get_recent_history()
    if not logs.empty:
        for _, row in logs.iterrows():
            st.sidebar.text(f"✅ {row['action_type']}\n{row['timestamp'].strftime('%H:%M')}")
    else:
        st.sidebar.caption("Henüz işlem yapılmadı.")
except:
    st.sidebar.caption("Loglar yükleniyor...")
