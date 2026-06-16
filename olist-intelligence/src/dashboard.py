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

# --- AUTO INGESTION (For Streamlit Cloud / SQLite) ---
# Checks if DB exists on startup, if not, triggers ingest (Kaggle Download -> SQLite)
import os
from src.config import DATABASE_URL, DATA_RAW_PATH
from src.ml.ingest import OlistIngestor

if "sqlite" in DATABASE_URL:
    db_path = DATABASE_URL.replace("sqlite:///", "")
    # Check if DB missing or too small (empty)
    if not os.path.exists(db_path) or os.path.getsize(db_path) < 1000:
        placeholder = st.empty()
        with placeholder.container():
            st.info("🚀 İlk kurulum yapılıyor (Veri indiriliyor & Veritabanı oluşturuluyor)...")
            st.warning("⚠️ Bu işlem internet hızına bağlı olarak 1-2 dakika sürebilir. Lütfen bekleyin.")
            
            try:
                ingestor = OlistIngestor(DATABASE_URL, str(DATA_RAW_PATH))
                ingestor.run()
                st.success('✅ Kurulum tamamlandı! Uygulama başlatılıyor...')
            except Exception as e:
                st.error(f"❌ Kurulum hatası: {e}")
                st.stop()
                
        placeholder.empty()
        st.rerun()

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
    # Fallback if DB is empty or returns None
    if pd.isnull(min_date):
        min_date = pd.to_datetime("2016-01-01")
        max_date = pd.to_datetime("2018-12-31")
except:
    min_date = pd.to_datetime("2016-01-01")
    max_date = pd.to_datetime("2018-12-31")

# Ensure dates are valid
if min_date > max_date:
    min_date, max_date = max_date, min_date

start_date = st.sidebar.date_input("Başlangıç", min_date, min_value=min_date, max_value=max_date)
end_date = st.sidebar.date_input("Bitiş", max_date, min_value=min_date, max_value=max_date)

if start_date > end_date:
    st.sidebar.error("Hata: Başlangıç tarihi bitiş tarihinden sonra olamaz.")
    # Auto-correct logic could go here, but warning is safer for now.

st.sidebar.markdown("---")
st.sidebar.subheader("Runtime")
readiness = action_service.api_client.get_readiness()
if readiness:
    generated_tables = readiness.get("generated_tables", {})
    loaded_models = readiness.get("loaded_models", [])
    table_status = ", ".join(
        name for name, is_ready in generated_tables.items() if is_ready
    ) or "none"
    model_status = ", ".join(loaded_models) or "none"
    st.sidebar.caption(f"Generated tables: {table_status}")
    st.sidebar.caption(f"Loaded models: {model_status}")
else:
    st.sidebar.caption("API readiness unavailable; action widgets may be degraded.")

st.sidebar.info("v3.1.0 - Enhanced Analytics")

# --- CONTROLLER LOGIC ---

if page == "Ana Sayfa":
    metrics = analytics_service.get_daily_pulse(start_date, end_date)
    executive_data = analytics_service.get_executive_dashboard_data(start_date, end_date)
    home_view.render_home_view(metrics, executive_data)

elif page == "📦 Operasyon Merkezi":
    risk_count, metrics, df_details = analytics_service.get_logistics_data(start_date, end_date)
    logistics_view.render_logistics_view(risk_count, metrics, df_details)

elif page == "🤝 Müşteri Sadakati":
    customer_metrics = analytics_service.get_daily_pulse(start_date, end_date)
    customer_view.render_customer_view(customer_metrics)

elif page == "📊 Segmentasyon Analizi":
    df_growth = analytics_service.get_segmentation_data()
    growth_view.render_growth_view(df_growth)

elif page == "📈 Ranking & Trends":
    # Pass date filters to ranking view
    ranking_view.render_ranking_view(start_date, end_date)

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
