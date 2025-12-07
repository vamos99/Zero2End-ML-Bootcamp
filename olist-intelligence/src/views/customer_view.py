import streamlit as st
from src.services import action_service, analytics_service
from src.database import repository
from src.services.api_client import api_client

def render_customer_view(risk_churn):
    st.title("🤝 Müşteri Sadakati (Retention)")
    
    # Calculate dynamic at-risk revenue (avg customer value * risk count)
    avg_customer_value = 150  # Average order value in BRL
    at_risk_revenue = risk_churn * avg_customer_value * 3  # Estimate 3 orders/year
    
    # KPI
    col1, col2 = st.columns(2)
    with col1:
        st.metric("🔥 Churn Riski (Yüksek)", f"{risk_churn} Müşteri", help="Bizi terk etme olasılığı (Churn Score) yüksek olan müşteriler.")
    with col2:
        st.metric("💰 Risk Altındaki Ciro", f"{at_risk_revenue:,.0f} BRL", help="Riskli müşterilerin toplam yıllık harcama potansiyeli.")
        
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

    st.markdown("---")
    
    # NEW: Recommender System UI
    st.markdown("### 🔮 Kişiselleştirilmiş Ürün Önerileri (Smart Recommender)")
    
    with st.expander("🛍️ Müşteri Öneri Motoru", expanded=True):
        st.info("Bu modül, SVD (Singular Value Decomposition) algoritması kullanarak müşteriye özel ürün önerileri sunar.")
        
        # Random ID Logic
        col_in, col_btn = st.columns([3, 1])
        
        default_id = "871766c5855e863f6eccc05f988b23"
        if "random_id" in st.session_state:
            default_id = st.session_state.random_id

        with col_in:
            c_input = st.text_input("Müşteri ID:", value=default_id)
        
        with col_btn:
             st.write("") # Spacer
             st.write("")
             if st.button("🎲 Rastgele", help="Veritabanından gerçek bir müşteri seç"):
                 st.session_state.random_id = repository.get_random_customer_id()
                 st.rerun()
        
        if st.button("Önerileri Getir 🧠", key="rec_btn"):
            with st.spinner("Yapay Zeka düşünüyor..."):
                rec_result = action_service.get_recommendations(c_input)
            
            if "error" in rec_result:
                st.error(rec_result["error"])
            else:
                st.success(f"Yöntem: {rec_result.get('method', 'Bilinmiyor')}")
                st.write("**Önerilen Ürünler:**")
                
                # Cards layout for products
                cols = st.columns(5)
                products = rec_result.get("recommendations", [])
                
                for i, prod in enumerate(products):
                    if i < 5:
                        with cols[i]:
                            # Clean string just in case
                            prod_str = str(prod).strip()
                            st.image("https://placehold.co/150x150?text=Product", caption=prod_str)

    st.markdown("---")
    
    # NEW: Churn Calculator
    st.markdown("### 🔥 Churn Riski Hesaplayıcı (Simülasyon)")
    
    with st.expander("👤 Tekil Müşteri Analizi Yap", expanded=False):
        with st.form("churn_prediction_form"):
            c1, c2, c3 = st.columns(3)
            
            with c1:
                recency = st.number_input("Son Sipariş Üzerinden Geçen Gün", value=30, step=1)
            with c2:
                freq = st.number_input("Toplam Sipariş Sayısı", value=1, step=1)
            with c3:
                money = st.number_input("Toplam Harcama (BRL)", value=100.0, step=10.0)
                
            submitted = st.form_submit_button("Risk Hesapla 🚨")
            
        if submitted:
            with st.spinner("Model tahmin yapıyor..."):
                result = api_client.predict_churn(
                    days_since=recency,
                    frequency=freq,
                    monetary=money
                )
                
            if result:
                prob = result.get('churn_probability', 0)
                risk = result.get('risk_level', 'Unknown')
                
                st.write(f"**Churn İhtimali:** %{prob*100:.1f}")
                
                if prob > 0.7:
                    st.error(f"Risk Seviyesi: {risk} (Çok Yüksek)")
                elif prob > 0.4:
                    st.warning(f"Risk Seviyesi: {risk} (Orta)")
                else:
                    st.success(f"Risk Seviyesi: {risk} (Düşük)")
            else:
                st.error("API Hatası! Uvicorn çalışıyor mu?")
