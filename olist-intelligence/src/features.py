import numpy as np

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    İki nokta arasındaki Haversine mesafesini (km) hesaplar.
    Vektörize işlem (NumPy) kullanır.
    """
    R = 6371  # Dünya yarıçapı (km)

    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)

    a = np.sin(delta_phi / 2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    d = R * c
    return d


def review_score_to_sentiment(score):
    """
    Review puanını sentiment kategorisine çevirir.
    1-2: Negative (-1)
    3: Neutral (0)
    4-5: Positive (1)
    """
    if score <= 2:
        return -1
    elif score == 3:
        return 0
    else:
        return 1


def calculate_seller_metrics(df_reviews, df_items):
    """
    Satıcı bazlı review metrikleri hesaplar.
    Returns: seller_id, avg_rating, review_count, negative_ratio
    """
    # Items ile reviews birleştir
    merged = df_items.merge(df_reviews, on='order_id', how='left')
    
    # Satıcı bazlı agregasyon
    seller_stats = merged.groupby('seller_id').agg({
        'review_score': ['mean', 'count'],
    }).reset_index()
    
    seller_stats.columns = ['seller_id', 'avg_rating', 'review_count']
    
    # Negatif oranı hesapla
    merged['is_negative'] = merged['review_score'].apply(lambda x: 1 if x <= 2 else 0)
    negative_ratio = merged.groupby('seller_id')['is_negative'].mean().reset_index()
    negative_ratio.columns = ['seller_id', 'negative_ratio']
    
    seller_stats = seller_stats.merge(negative_ratio, on='seller_id', how='left')
    
    return seller_stats

