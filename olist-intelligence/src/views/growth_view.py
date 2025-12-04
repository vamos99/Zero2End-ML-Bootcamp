import streamlit as st
import plotly.express as px

def render_growth_view(df_growth):
    st.title("📊 Segmentasyon Analizi")
    st.markdown("""
    **Amaç:** Müşteri tabanını segmentlere ayırarak her gruba özel pazarlama stratejileri geliştirmek.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig1 = px.bar(df_growth, x="Segment Adı", y="count", title="Müşteri Sayısı (Segment Bazlı)", color="Segment Adı")
        st.plotly_chart(fig1, width=600) # Using fixed width or let streamlit handle it
        
    with col2:
        fig2 = px.bar(df_growth, x="Segment Adı", y="avg_spend", title="Ortalama Harcama (Segment Bazlı)", color="Segment Adı")
        st.plotly_chart(fig2, width=600)
        
    st.subheader("💡 Stratejik Aksiyon Planı")
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.info("**🏆 Şampiyonlar**\n\n*Özel VIP destek hattı verin.*")
    with c2:
        st.success("**💎 Sadık Müşteriler**\n\n*Sadakat programına dahil edin.*")
    with c3:
        st.warning("**🌱 Yeni Potansiyeller**\n\n*Hoşgeldin indirimi tanımlayın.*")
    with c4:
        st.error("**⚠️ Kayıp Riski**\n\n*Sizi özledik kuponu gönderin.*")
        
    st.markdown("---")
    st.subheader("📊 Detaylı Metrikler")
    st.dataframe(df_growth.style.format({"avg_spend": "{:.2f} BRL", "avg_recency": "{:.1f} Gün", "avg_freq": "{:.2f}"}))
