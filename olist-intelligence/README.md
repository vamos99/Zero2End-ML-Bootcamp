# Olist Intelligence Suite

Brezilya'nın en büyük e-ticaret platformu Olist'in verilerini kullanarak geliştirilmiş uçtan uca Veri Bilimi ve İş Zekası çözümü.

---

## Problem & Çözüm

### Problem 1: Teslimat Gecikmesi
**Sorun:** Müşteriler siparişlerin ne zaman geleceğini bilemiyor, gecikmeler şikayete dönüşüyor.

**Çözüm:** RandomForest modeli ile teslimat süresi tahmini (RMSE: 7.60 gün)

**Neden Bu Yaklaşım?**
- Haversine mesafe (satıcı-müşteri arası) en önemli faktör
- Satıcı puanı (review verisi) teslimat performansıyla ilişkili
- Aynı eyalet = daha hızlı teslimat

### Problem 2: Müşteri Kaybı (Churn)
**Sorun:** Hangi müşterilerin platformu terk edeceğini önceden tahmin edemiyoruz.

**Çözüm:** Zaman bazlı Churn tanımı (90 gün inaktif = Churn)

**Neden Bu Yaklaşım?**
- İlk yaklaşımda AUC %100 çıkıyordu - bu data leakage'dı
- Cluster'dan türetilen target gerçekçi değildi
- Gerçek tanım: %80.3 Churn Rate (anlamlı)

### Problem 3: Müşteri Tek Tip Görülüyor
**Sorun:** Tüm müşterilere aynı pazarlama yapılıyor.

**Çözüm:** RFM + K-Means ile segmentasyon (5 segment)

---

## Teknoloji Tercihleri

| Teknoloji | Neden? |
|-----------|--------|
| PostgreSQL | SQLite çoklu kullanıcıda kilitlenir, production için uygun değil |
| Streamlit | React ile aylar sürecek işi günlere indirir |
| Docker | "Benim bilgisayarımda çalışıyordu" problemini çözer |
| Polars | ETL'de Pandas'tan 10x hızlı |
| FastAPI | Modern, async, otomatik dokümantasyon |

---

## Özellikler

### Lojistik Tahmin
- RMSE: 7.60 gün
- Özellikler: mesafe, kargo, fiyat, ağırlık, satıcı puanı

### Churn Tahmini
- Rate: %80.3
- Tanım: 90 gün sipariş yok = Churn

### Müşteri Segmentasyonu
- 5 segment: Şampiyonlar, Sadıklar, Potansiyeller, Riskli, Uyuyanlar

### Dashboard
- 5 sayfa: Ana Sayfa, Operasyon, Müşteri, Segmentasyon, Ranking
- ROI simülasyonu

### API
- 4 endpoint: /predict/delivery, /predict/churn, /recommend, /segments
- X-API-KEY koruması

---

## Kurulum

```bash
# Klonla
git clone https://github.com/kullaniciadi/olist-intelligence.git
cd olist-intelligence

# Başlat
docker-compose up --build

# Erişim
# Dashboard: http://localhost:8501
# API Docs: http://localhost:8000/docs
```

---

## Dosya Yapısı

```
src/
├── views/           # Ekranlar (MVC - View)
├── services/        # İş mantığı (MVC - Controller)
├── database/        # Veri erişimi (MVC - Model)
├── app.py           # FastAPI
├── dashboard.py     # Streamlit
└── benchmark_models.py  # Model karşılaştırma

notebooks/
├── 1_eda.ipynb      # Veri keşfi
├── 2_logistics.ipynb # Teslimat modeli
├── 3_customer.ipynb  # Churn analizi
├── 4_growth.ipynb    # Segmentasyon
├── 5_evaluation.ipynb # Sonuçlar
└── 6_executive.ipynb # Sunum için
```

---

## Model Performansı

| Model | Metrik | Değer |
|-------|--------|-------|
| Lojistik (RandomForest) | RMSE | 7.60 gün |
| Churn | Rate | %80.3 |
| Recommender (SVD) | Coverage | 99K user |

**Feature Importance (Lojistik):**
1. distance_km (Haversine)
2. freight_value
3. price
4. seller_avg_rating
5. product_weight_g
6. same_state

---

## Veritabanı Optimizasyonu

11 index eklendi:
- orders: customer_id, status, purchase_date
- order_items: order_id, product_id, seller_id
- geolocation: zip_code_prefix

---

## CI/CD

GitHub Actions ile:
- Push/PR'da otomatik test
- Syntax kontrolü (flake8)

---

**Versiyon:** 3.0 | **Güncelleme:** Aralık 2024
