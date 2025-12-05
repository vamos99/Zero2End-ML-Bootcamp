import streamlit as st
import plotly.express as px
from src.database import repository

def render_ranking_view():
    st.title("📈 Ranking & Trends")
    st.markdown("""
    **Amaç:** En çok satan ürünler, en iyi satıcılar ve kategori performanslarını analiz etmek.
    """)
    
    # Tab layout for different rankings
    tab1, tab2, tab3 = st.tabs(["🛍️ Ürün Sıralaması", "🏪 Satıcı Sıralaması", "📊 Kategori Analizi"])
    
    with tab1:
        st.subheader("En Çok Satan Ürünler (Top 20)")
        try:
            df_products = repository.get_top_products(limit=20)
            if not df_products.empty:
                fig = px.bar(df_products, x='product_category', y='total_sales', 
                            title="Kategoriye Göre Satış", color='total_sales',
                            color_continuous_scale='Viridis')
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(df_products.style.format({"total_sales": "{:,.0f} BRL", "order_count": "{:,}"}))
            else:
                st.info("Ürün verisi bulunamadı.")
        except Exception as e:
            st.warning(f"Veri yüklenemedi: {e}")
    
    with tab2:
        st.subheader("En İyi Satıcılar (Top 20)")
        try:
            df_sellers = repository.get_top_sellers(limit=20)
            if not df_sellers.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    fig1 = px.bar(df_sellers.head(10), x='seller_id', y='total_revenue',
                                 title="Ciro Bazlı Top 10", color='avg_rating',
                                 color_continuous_scale='RdYlGn')
                    st.plotly_chart(fig1, use_container_width=True)
                
                with col2:
                    fig2 = px.scatter(df_sellers, x='order_count', y='avg_rating',
                                     size='total_revenue', color='on_time_rate',
                                     hover_name='seller_id',
                                     title="Performans Matrisi",
                                     labels={'order_count': 'Sipariş Sayısı', 'avg_rating': 'Ortalama Puan'})
                    st.plotly_chart(fig2, use_container_width=True)
                
                st.dataframe(df_sellers.style.format({
                    "total_revenue": "{:,.0f} BRL", 
                    "avg_rating": "{:.2f} ⭐",
                    "on_time_rate": "{:.1f}%"
                }))
            else:
                st.info("Satıcı verisi bulunamadı.")
        except Exception as e:
            st.warning(f"Veri yüklenemedi: {e}")
    
    with tab3:
        st.subheader("Kategori Performansı")
        try:
            df_categories = repository.get_category_performance()
            if not df_categories.empty:
                fig = px.treemap(df_categories, path=['category'], values='revenue',
                                color='avg_review', color_continuous_scale='RdYlGn',
                                title="Kategori Ağacı (Gelir & Puan)")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Kategori verisi bulunamadı.")
        except Exception as e:
            st.warning(f"Veri yüklenemedi: {e}")
