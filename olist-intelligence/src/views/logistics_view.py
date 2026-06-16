import streamlit as st
from src.services import action_service
from src.services.api_client import api_client

def render_logistics_view(risk_count, metrics, df_details):
    st.title("📦 Operasyon Merkezi")
    available = metrics.get("available", False)
    
    # KPI Row
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("🚨 Uzun Teslimat Tahmini", f"{risk_count} Sipariş" if available else "Hazır değil", help="Tahmini teslimat süresi 10 günden uzun olan sipariş sayısı.")
    with col2:
        st.metric("✅ Model Karşılama Oranı", f"%{metrics['on_time_rate']:.1f}" if available else "Hazır değil", help="Gerçek teslimat süresi model tahminini aşmayan siparişlerin oranı; SLA metriği değildir.")
    with col3:
        st.metric("⏱️ Ort. Teslimat Süresi", f"{metrics['avg_time']:.1f} Gün" if available else "Hazır değil", help="Sipariş veriliş tarihinden teslimat tarihine kadar geçen ortalama süre.")

    st.markdown("---")

    # BI Action Section
    if not available:
        st.info("Lojistik tahmin çıktısı bulunamadı. `logistics_predictions` tablosunu local build veya Logistics notebook ile üretin.")
    elif risk_count > 0:
        low_review_rate = metrics['low_review_rate']
        st.warning(f"Risk grubundaki siparişlerin %{low_review_rate:.1f} kadarı 1-2 yıldızlı review ile ilişkilidir. Bu ilişki nedensel etki değildir.")
        
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown("**Deney Hipotezi:** Proaktif bilgilendirme düşük review oranını azaltabilir.")
            st.caption("Beklenen etki ölçülmemiştir; önce holdout gruplu iletişim deneyi tasarlanmalıdır.")
            
        with c2:
            if st.button("İletişim Deney Taslağını Kaydet", key="logistics_btn"):
                action_service.execute_action("LOGISTICS_EXPERIMENT_DRAFT", f"{risk_count} sipariş için iletişim deney taslağı.", risk_count)
                st.success("İletişim deney taslağı işlem günlüğüne kaydedildi; gerçek mesaj gönderilmedi.")

        # Detailed Table
        st.subheader("📋 İncelenecek Siparişler")
        st.dataframe(df_details.style.highlight_max(axis=0, color='#ffcdd2'), width="stretch")
    else:
        st.success("Seçili tarih aralığında 10 günden uzun teslimat tahmini görünmüyor.")

    st.markdown("---")

    # NEW: Prediction Simulator
    st.markdown("### 🤖 Teslimat Modeli Simülatörü")
    
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
            with st.spinner("Yüklü model kontrol ediliyor..."):
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
                    st.warning(f"Risk Seviyesi: {risk}")
                else:
                    st.info(f"Risk Seviyesi: {risk}")
            else:
                detail = (api_client.last_error or {}).get("detail")
                if detail == "Model not loaded":
                    st.warning("Teslimat modeli yüklü değil. Operasyon metrikleri hazır tabloyu kullanır; bu simülatör için yerel model artefact'ı gerekir.")
                else:
                    st.error(f"Teslimat tahmini alınamadı: {detail or 'API yanıtı yok.'}")
