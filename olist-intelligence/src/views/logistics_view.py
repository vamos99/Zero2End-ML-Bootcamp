import streamlit as st
from src.services import action_service
from src.services.api_client import api_client

def render_logistics_view(risk_count, metrics, df_details):
    st.title("📦 Operasyon Merkezi")
    
    # KPI Row
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("🚨 Gecikme Riski Olanlar", f"{risk_count} Sipariş", help="Tahmini teslimat süresi, söz verilen süreyi geçen sipariş sayısı.")
    with col2:
        st.metric("✅ Zamanında Teslimat Oranı", f"%{metrics['on_time_rate']:.1f}", help="Söz verilen tarihte veya öncesinde teslim edilen siparişlerin oranı.")
    with col3:
        st.metric("⏱️ Ort. Teslimat Süresi", f"{metrics['avg_time']:.1f} Gün", help="Sipariş veriliş tarihinden teslimat tarihine kadar geçen ortalama süre.")

    st.markdown("---")

    # BI Action Section
    if risk_count > 0:
        # Dynamic Impact Calculation
        complaint_rate = metrics['complaint_rate']
        potential_complaints = int(risk_count * (complaint_rate / 100.0))
        
        st.warning(f"⚠️ **Analiz:** {risk_count} siparişin gecikmesi, tahmini **{potential_complaints} Müşteri Şikayeti** yaratabilir (Beklenen Şikayet Oranı: %{complaint_rate:.1f}).")
        
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown("**Önerilen Aksiyon:** Otomatik bilgilendirme e-postası gönder.")
            st.caption(f"Beklenen Etki: {int(potential_complaints * 0.8)} müşterinin şikayet etmesini önler.")
            
        with c2:
            if st.button("📧 E-Posta Gönder", key="logistics_btn"):
                action_service.execute_action("EMAIL_CAMPAIGN", f"{risk_count} riskli sipariş için bilgilendirme yapıldı.", risk_count)
                st.success("Aksiyon Başarılı! İşlem günlüğe kaydedildi.")
                st.balloons()

        # Detailed Table
        st.subheader("📋 Müdahale Gerektiren Siparişler")
        st.dataframe(df_details.style.highlight_max(axis=0, color='#ffcdd2'), width="stretch")
    else:
        st.success("Harika! Şu an riskli bir sipariş görünmüyor.")

    st.markdown("---")

    # NEW: Prediction Simulator
    st.markdown("### 🤖 Yapay Zeka Teslimat Tahmini (Simülasyon)")
    
    with st.expander("🚚 Yeni Bir Sipariş İçin Tahmin Yap", expanded=False):
        with st.form("logistics_prediction_form"):
            c1, c2, c3 = st.columns(3)
            
            with c1:
                price = st.number_input("Ürün Fiyatı (BRL)", value=50.0, step=10.0)
                freight = st.number_input("Kargo Ücreti (BRL)", value=15.0, step=5.0)
                
            with c2:
                weight = st.number_input("Ağırlık (g)", value=500, step=100)
                distance = st.number_input("Mesafe (km)", value=300, step=50)

            with c3:
                seller_score = st.slider("Satıcı Puanı", 1.0, 5.0, 4.0)
                same_state = st.toggle("Aynı Eyalet?", value=True)
                
            submitted = st.form_submit_button("Tahmin Et ⏱️")
            
        if submitted:
            with st.spinner("Model çalışıyor..."):
                # Call API
                result = api_client.predict_delivery(
                    freight=freight,
                    price=price,
                    weight=weight,
                    desc_length=500, # Default
                    distance=distance,
                    same_state=1 if same_state else 0,
                    seller_rating=seller_score
                )
                
            if result:
                days = result.get('predicted_days', 0)
                risk = result.get('risk_level', 'Unknown')
                
                st.success(f"**Tahmini Teslimat:** {days:.1f} Gün")
                if risk == "High":
                    st.error(f"Risk Seviyesi: {risk}")
                else:
                    st.info(f"Risk Seviyesi: {risk}")
            else:
                st.error("API Bağlantı Hatası! (Uvicorn çalışıyor mu?)")
