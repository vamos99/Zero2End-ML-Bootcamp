import streamlit as st
from src.services import action_service, analytics_service

def render_customer_view(risk_churn):
    st.title("🤝 Müşteri Sadakati (Retention)")
    
    # KPI
    col1, col2 = st.columns(2)
    with col1:
        st.metric("🔥 Churn Riski (Yüksek)", f"{risk_churn} Müşteri")
    with col2:
        st.metric("💰 Risk Altındaki Ciro", "450.000 BRL")
        
    st.markdown("---")
    
    st.subheader("🎯 Hedefli Kampanya Simülasyonu")
    
    action = st.radio("Aksiyon Seçiniz:", ["%15 İndirim Tanımla", "Sadakat Puanı Yükle", "Müşteri Temsilcisi Arasın"], horizontal=True)
    
    sim = action_service.simulate_impact(action)
    
    k1, k2, k3 = st.columns(3)
    k1.metric("Tahmini Maliyet", f"{sim['cost']} BRL", delta="Yatırım", delta_color="inverse")
    k2.metric("Kurtarılan Ciro", f"{sim['saved']} BRL", delta="Kazanç")
    k3.metric("Tahmini ROI", sim['roi'])
    
    if st.button("Kampanyayı Başlat 🚀", key="churn_btn"):
        action_service.execute_action("CHURN_CAMPAIGN", f"{action} kampanyası başlatıldı.", sim['saved'])
        st.balloons()
        st.success(f"Kampanya başlatıldı! Tahmini {sim['saved']} BRL ciro kurtarılacak.")
    
    st.markdown("---")
    
    # Target Audience Builder
    st.markdown("### 🔍 Hedef Kitle Oluşturucu")
    
    selected_segment = st.selectbox("Segment Seçiniz:", ["Tümü", "💎 Sadık Müşteriler", "🏆 Şampiyonlar", "⚠️ Kayıp Riski", "🌱 Yeni Potansiyeller"])
    
    try:
        df_target = analytics_service.get_target_audience_data(selected_segment)
        
        # Show preview
        st.dataframe(df_target.head(10))
        
        # Export Button
        csv = df_target.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Hedef Kitleyi İndir (CSV)",
            data=csv,
            file_name=f'hedef_kitle_{selected_segment}.csv',
            mime='text/csv',
        )
        
    except Exception as e:
        st.warning(f"Veri yüklenemedi: {e}")
