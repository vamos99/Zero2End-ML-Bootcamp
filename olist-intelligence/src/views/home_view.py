import streamlit as st

def render_home_view(metrics):
    st.title("📊 Yönetici Özeti (Executive Summary)")
    st.markdown("### 📅 Günlük Nabız (Daily Pulse)")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("📦 Toplam Sipariş", f"{metrics['total_orders']:,}")
    
    with col2:
        if metrics['risk_logistics'] > 0:
            st.metric("🚨 Lojistik Riski", f"{metrics['risk_logistics']} Sipariş", delta="Müdahale Et", delta_color="inverse")
        else:
            st.metric("✅ Lojistik Durumu", "Stabil")
            
    with col3:
        if metrics['risk_churn'] > 0:
            st.metric("🔥 Churn Riski", f"{metrics['risk_churn']} Müşteri", delta="Kampanya Başlat", delta_color="inverse")
        else:
            st.metric("✅ Müşteri Durumu", "Stabil")

    st.markdown("---")
    
    st.info("""
    **👋 Hoşgeldiniz! Bugün ne yapmak istersiniz?**
    
    *   **Operasyon:** Geciken siparişleri yönetmek için **'Operasyon Merkezi'**ne gidin.
    *   **Pazarlama:** Riskli müşterileri kurtarmak için **'Müşteri Sadakati'**ne gidin.
    *   **Strateji:** Büyüme fırsatlarını görmek için **'Segmentasyon Analizi'**ne gidin.
    """)
