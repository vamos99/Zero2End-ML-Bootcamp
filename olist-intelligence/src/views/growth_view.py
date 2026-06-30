import streamlit as st
import plotly.express as px

def render_growth_view(df_growth):
    st.title("📊 Segmentasyon Analizi")
    st.markdown("""
    **Amaç:** Müşteri tabanını segmentlere ayırarak her gruba özel pazarlama stratejileri geliştirmek.
    """)
    
    if df_growth.empty:
        st.info("Segmentasyon çıktısı bulunamadı. `customer_segments` tablosunu local build veya Growth notebook ile üretin.")
        return

    col1, col2 = st.columns(2)
    
    with col1:
        fig1 = px.bar(df_growth, x="Segment Adı", y="count", title="Müşteri Sayısı (Segment Bazlı)", color="Segment Adı")
        st.plotly_chart(fig1, width=600) # Using fixed width or let streamlit handle it
        
    with col2:
        fig2 = px.bar(df_growth, x="Segment Adı", y="avg_spend", title="Ortalama Harcama (Segment Bazlı)", color="Segment Adı")
        st.plotly_chart(fig2, width=600)
        
    st.subheader("💡 Deney Hipotezleri")
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.info("**💎 Champions**\n\n*Erken erişim teklifini kontrollü deneyle test et.*")
    with c2:
        st.success("**🏆 Loyal**\n\n*Cross-sell teklifini holdout grupla ölç.*")
    with c3:
        st.warning("**🌱 Developing**\n\n*İkinci sipariş onboarding deneyini test et.*")
    with c4:
        st.info("**⚠️ At Risk**\n\n*Düşük maliyetli reaktivasyon mesajını test et.*")
        
    st.markdown("---")
    st.subheader("📊 Detaylı Metrikler")
    st.dataframe(df_growth.style.format({"avg_spend": "{:.2f} BRL", "avg_recency": "{:.1f} Gün", "avg_freq": "{:.2f}"}))
