import streamlit as st
from src.services import action_service, analytics_service
from src.database import repository
from src.services.api_client import api_client

def render_customer_view(metrics):
    st.title("🤝 Müşteri Sadakati (Retention)")

    risk_churn = metrics.get("risk_churn", 0)
    segments_available = metrics.get("generated_outputs", {}).get("customer_segments", False)
    observed_value = risk_churn * metrics.get("revenue_per_customer", 0)
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "At Risk Segmenti",
            f"{risk_churn} müşteri" if segments_available else "Hazır değil",
            help="Growth notebook tarafından göreli RFM profili olarak At Risk etiketi verilen müşteri sayısı.",
        )
    with col2:
        st.metric(
            "Gözlenen Değer Göstergesi",
            f"{observed_value:,.0f} BRL" if segments_available else "Hazır değil",
            help="At Risk müşteri sayısı ile seçili dönemde gözlenen müşteri başı ürün cirosunun çarpımı; tahmin veya yıllık gelir değildir.",
        )

    if not segments_available:
        st.info("Segmentasyon çıktısı bulunamadı. `customer_segments` tablosunu local build veya Growth notebook ile üretin.")
        
    st.markdown("---")
    
    st.subheader("🎯 Kampanya Deney Taslağı")
    
    action = st.radio("Aksiyon Seçiniz:", ["%15 İndirim Tanımla", "Sadakat Puanı Yükle", "Müşteri Temsilcisi Arasın"], horizontal=True)
    
    sim = action_service.simulate_impact(action)
    
    st.info(
        f"Ölçülecek ana sonuç: **{sim['hypothesis']}**. "
        "Maliyet, uplift ve ROI ancak kontrol gruplu deney sonrasında raporlanmalıdır."
    )
    st.caption(
        f"Metrik: `{sim['metric']}` | Baseline: {sim['baseline_source']} | "
        f"Kanıt ihtiyacı: {sim['evidence_needed']}"
    )
    
    if st.button("Deney Taslağını Günlüğe Kaydet", key="churn_btn"):
        action_service.execute_action("RETENTION_EXPERIMENT_DRAFT", f"{action} deney taslağı oluşturuldu.", 0)
        st.success("Deney taslağı işlem günlüğüne kaydedildi; gerçek kampanya başlatılmadı.")
    
    st.markdown("---")
    
    # Target Audience Builder
    st.markdown("### 🔍 Hedef Kitle Oluşturucu")
    
    selected_segment = st.selectbox(
        "Segment Seçiniz:",
        ["Tümü", "💎 Champions", "🏆 Loyal", "⚠️ At Risk", "🌱 Developing"],
    )
    
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
    st.markdown("### 🔮 Ürün Öneri Prototipi")
    
    with st.expander("🛍️ Müşteri Öneri Motoru", expanded=True):
        st.info("SVD modeli varsa kişiselleştirilmiş ürün kimlikleri, yoksa popüler kategori fallback'i döner.")
        
        # Random ID Logic
        col_in, col_btn = st.columns([3, 1])
        
        default_id = "8d50f5eadf50201ccdcedfb9e2ac8455"
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
                method = rec_result.get("method", "unknown")
                item_type = rec_result.get("item_type", "product_id")
                if method.startswith("popularity_fallback"):
                    st.warning("Kişiselleştirilmiş öneri modeli yüklü değil; popüler kategori fallback'i gösteriliyor.")
                else:
                    st.success("Kişiselleştirilmiş SVD ürün önerisi üretildi.")
                st.caption(f"Yöntem: `{method}` | Çıktı tipi: `{item_type}`")
                label = "Kategori çıktıları" if item_type == "product_category" else "Ürün kimlikleri"
                st.write(f"**{label}:**")
                
                # Cards layout for products
                cols = st.columns(5)
                products = rec_result.get("recommendations", [])
                
                for i, prod in enumerate(products):
                    if i < 5:
                        with cols[i]:
                            # Clean string just in case
                            prod_str = str(prod).strip()
                            st.code(prod_str)

    st.markdown("---")
    
    # NEW: Churn Calculator
    st.markdown("### 🔥 Repeat-Purchase Model Sandbox")
    
    with st.expander("👤 Tekil Müşteri Analizi Yap", expanded=False):
        st.caption("Yalnızca değerlendirme eşiğini geçen yerel model artefact'ı yüklüyse sonuç üretir.")
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
                detail = (api_client.last_error or {}).get("detail")
                if detail == "Model not loaded":
                    st.warning("Repeat-purchase modeli yüklü değil. Bu yerel snapshot model eşiğini geçmediyse sandbox sonuç üretmez.")
                else:
                    st.error(f"Churn tahmini alınamadı: {detail or 'API yanıtı yok.'}")
