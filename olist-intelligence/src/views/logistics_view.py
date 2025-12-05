import streamlit as st
from src.services import action_service

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
