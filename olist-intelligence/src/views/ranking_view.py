import streamlit as st
import plotly.express as px
from src.database import repository

def render_ranking_view(start_date=None, end_date=None):
    st.title("📈 Ranking & Trends")
    st.markdown("""
    **Amaç:** En çok satan ürünler, en iyi satıcılar ve kategori performanslarını analiz etmek.
    """)
    
    # Tab layout for different rankings
    tab1, tab2, tab3 = st.tabs(["🛍️ Ürün Sıralaması", "🏪 Satıcı Sıralaması", "📊 Kategori Analizi"])
    
    with tab1:
        st.subheader("En Çok Satan Ürünler (Top 20)")
        try:
            df_products = repository.get_top_products(limit=20, start_date=start_date, end_date=end_date)
            if not df_products.empty:
                fig = px.bar(df_products, x='product_category', y='total_sales', 
                            title="Kategoriye Göre Satış", color='total_sales',
                            color_continuous_scale='Viridis',
                            labels={'product_category': 'Kategori', 'total_sales': 'Toplam Satış (BRL)'})
                st.plotly_chart(fig, width="stretch")
                
                st.dataframe(df_products.style.format({"total_sales": "{:,.0f} BRL", "order_count": "{:,}"}))
            else:
                st.info("Ürün verisi bulunamadı.")
        except Exception as e:
            st.warning(f"Veri yüklenemedi: {e}")
    
    with tab2:
        st.subheader("En İyi Satıcılar (Top 20)")
        try:
            df_sellers = repository.get_top_sellers(limit=20, start_date=start_date, end_date=end_date)
            if not df_sellers.empty:
                # Add readable seller names (short version of ID)
                df_sellers['seller_name'] = df_sellers['seller_id'].apply(lambda x: f"Satıcı #{x[:8]}..." if len(x) > 8 else f"Satıcı #{x}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    fig1 = px.bar(df_sellers.head(10), x='seller_name', y='total_revenue',
                                 title="Ciro Bazlı Top 10", color='avg_rating',
                                 color_continuous_scale='RdYlGn',
                                 labels={'seller_name': 'Satıcı', 'total_revenue': 'Toplam Ciro (BRL)', 'avg_rating': 'Ortalama Puan'})
                    fig1.update_xaxes(tickangle=45)
                    st.plotly_chart(fig1, width="stretch")
                
                with col2:
                    fig2 = px.scatter(df_sellers, x='order_count', y='avg_rating',
                                     size='total_revenue', color='on_time_rate',
                                     hover_name='seller_name',
                                     title="Performans Matrisi",
                                     labels={'order_count': 'Sipariş Sayısı', 'avg_rating': 'Ortalama Puan', 'on_time_rate': 'Zamanında Teslimat %'})
                    st.plotly_chart(fig2, width="stretch")
                
                # Display table with formatted seller names
                display_df = df_sellers[['seller_name', 'order_count', 'total_revenue', 'avg_rating', 'on_time_rate']].copy()
                display_df.columns = ['Satıcı', 'Sipariş Sayısı', 'Toplam Ciro', 'Ortalama Puan', 'Zamanında Teslimat %']
                st.dataframe(display_df.style.format({
                    "Toplam Ciro": "{:,.0f} BRL", 
                    "Ortalama Puan": "{:.2f} ⭐",
                    "Zamanında Teslimat %": "{:.1f}%"
                }))
            else:
                st.info("Satıcı verisi bulunamadı.")
        except Exception as e:
            st.warning(f"Veri yüklenemedi: {e}")
    
    with tab3:
        st.subheader("Kategori Performansı")
        try:
            df_categories = repository.get_category_performance(start_date=start_date, end_date=end_date)
            if not df_categories.empty and len(df_categories) > 0:
                # Filter out null categories
                df_categories = df_categories[df_categories['category'].notna()]
                
                if not df_categories.empty:
                    fig = px.treemap(df_categories, path=['category'], values='revenue',
                                    color='avg_review', color_continuous_scale='RdYlGn',
                                    title="Kategori Ağacı (Gelir & Puan)",
                                    labels={'category': 'Kategori', 'revenue': 'Gelir', 'avg_review': 'Ort. Puan'})
                    st.plotly_chart(fig, width="stretch")
                    
                    # Additional bar chart for clarity
                    fig2 = px.bar(df_categories.head(15), x='category', y='revenue',
                                 color='avg_review', color_continuous_scale='RdYlGn',
                                 title="Top 15 Kategori (Gelir Bazlı)",
                                 labels={'category': 'Kategori', 'revenue': 'Gelir (BRL)', 'avg_review': 'Ort. Puan'})
                    fig2.update_xaxes(tickangle=45)
                    st.plotly_chart(fig2, width="stretch")
                else:
                    st.info("Kategori verisi bulunamadı.")
            else:
                st.info("Kategori verisi bulunamadı.")
        except Exception as e:
            st.warning(f"Veri yüklenemedi: {e}")
