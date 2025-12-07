# Olist Intelligence Suite

Brezilya'nın en büyük e-ticaret platformu Olist'in verilerini kullanarak geliştirilmiş uçtan uca Veri Bilimi ve İş Zekası çözümü.

---

## Problem & Çözüm

### Problem 1: Teslimat Gecikmesi
**Sorun:** Müşteriler siparişlerin ne zaman geleceğini bilemiyor, gecikmeler şikayete dönüşüyor.

**Çözüm:** CatBoost modeli ile teslimat süresi tahmini (RMSE: 7.60 gün)

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

### Ön Gereksinimler
- Docker & Docker Compose (v2+)
- Git
- 4GB+ RAM (Docker için)
- 10GB+ boş disk alanı

### Adımlar

```bash
# 1. Klonla
git clone https://github.com/vamos99/Zero2End-ML-Bootcamp.git
cd Zero2End-ML-Bootcamp/olist-intelligence

# 2. Veri dosyalarını hazırla (ilk kez)
# data/ klasörüne Olist CSV dosyalarını koy:
# - olist_orders_dataset.csv
# - olist_order_items_dataset.csv
# - olist_customers_dataset.csv
# - olist_geolocation_dataset.csv
# - olist_order_payments_dataset.csv
# - olist_order_reviews_dataset.csv
# - olist_products_dataset.csv
# - olist_sellers_dataset.csv
# - product_category_name_translation.csv

# 3. Docker ile başlat
docker-compose up --build -d

# 4. Veriyi yükle (ilk kez, başka terminalde)
docker exec olist_api python -m src.ml.ingest

# 5. Modelleri eğit (isteğe bağlı)
docker exec olist_api python -m src.ml.train
```

### Erişim Adresleri

| Servis | URL | Açıklama |
|--------|-----|----------|
| Dashboard | http://localhost:8501 | Streamlit BI Dashboard |
| API Docs | http://localhost:8000/docs | FastAPI Swagger UI |
| MLflow | http://localhost:5000 | Model Registry |

### Notebook'ları Çalıştırma

```bash
# Yerel Python ortamı gerekli
cd notebooks
pip install -r ../requirements.txt

# Jupyter başlat
jupyter notebook
```

**Not:** Notebook'lar PostgreSQL'e `localhost:5432` üzerinden bağlanır. Docker çalışıyor olmalı.

---

## Dosya Yapısı

```
src/
├── app.py          # FastAPI
├── dashboard.py    # Streamlit
├── ml/             # ML Core
│   ├── data.py     # Central Data Access
│   ├── features.py # Feature Engineering
│   ├── train.py    # Training Scripts
│   ├── ingest.py   # CSV → PostgreSQL
│   └── benchmark.py# Model Experiments
├── services/       # Services (Business Logic)
├── views/          # Dashboard Views
└── database/       # DB Connection & Queries

notebooks/
├── 1_general_eda_and_prep.ipynb  # Veri keşfi
├── 2_logistics_engine.ipynb      # Teslimat modeli
├── 3_customer_sentinel.ipynb     # Churn analizi
├── 4_growth_engine.ipynb         # Segmentasyon
├── 5_final_evaluation.ipynb      # Sonuçlar
└── 6_executive_pipeline.ipynb    # Executive sunum

data/               # CSV dosyaları (git'te yok)
models/             # Eğitilmiş modeller (.pkl)
```

---

## Model Performansı

| Model | Algoritma | Metrik | Değer |
|-------|-----------|--------|-------|
| Lojistik | CatBoost Regressor | RMSE | 7.8 gün |
| Churn | CatBoost Classifier | AUC | ~0.56 |
| Recommender | SVD (Matrix Factorization) | Coverage | 99K user |
| Segmentation | K-Means | Segments | 5 |

### Lojistik Model Features (10 adet)

| # | Feature | Açıklama |
|---|---------|----------|
| 1 | distance_km | Haversine mesafesi (km) |
| 2 | freight_value | Kargo ücreti |
| 3 | price | Ürün fiyatı |
| 4 | product_weight_g | Ürün ağırlığı (gram) |
| 5 | product_description_lenght | Ürün açıklama uzunluğu |
| 6 | same_state | Aynı eyalet mi? (0/1) |
| 7 | seller_avg_rating | Satıcı ortalama puanı |
| 8 | product_photos_qty | Ürün fotoğraf sayısı |
| 9 | product_volume | Ürün hacmi (cm³) |
| 10 | freight_ratio | Kargo/Fiyat oranı |

### Churn Model Features (RFM)

| Feature | Açıklama |
|---------|----------|
| days_since_last_order | Son siparişten bu yana gün (Recency) |
| frequency | Toplam sipariş sayısı |
| monetary | Toplam harcama (R$) |

---

## Sınırlamalar & Denenen İyileştirmeler

### Churn Model Sınırlamaları

| Sorun | Açıklama |
|-------|----------|
| Düşük AUC (~0.56) | Olist one-time purchase marketplace, %97 müşteri tek seferlik |
| Data Leakage Riski | `days_since_last_order` target tanımıyla örtüşüyor |
| Yüksek Imbalance | %90 churn oranı modeli zorluyor |

**Denenen İyileştirmeler:**
- `avg_review_score`, `payment_type`, `monetary_per_order` eklendi → Minimal etki
- `auto_class_weights='Balanced'` → AUC 0.56'da kaldı
- Feature crossing → Anlamlı iyileşme yok

**Sonuç:** Bu veri seti yapısı (marketplace, tek seferlik) için churn tahmini inherent olarak zor.

### Lojistik Model

**Denenen İyileştirmeler:**
- `freight_per_km`, `distance_x_weight`, `is_weekend`, `category_avg_delivery` → RMSE 7.8 (değişim yok)

---

## Troubleshooting

### PostgreSQL "No space left on device" Hatası

```bash
# Docker kaynaklarını temizle
docker system prune -a --volumes -f

# Docker Desktop'ta Memory: 4GB+, Disk: 20GB+ olmalı
```

### Windows'ta Çalıştırma

Docker Desktop for Windows gerekli. WSL2 backend önerilir.

```powershell
# PowerShell'de
docker-compose up --build -d
```

### Notebook Veritabanı Hatası

Docker çalışıyor olmalı:
```bash
docker-compose ps  # db servisi UP olmalı
```

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

**Versiyon:** 3.1 | **Güncelleme:** Aralık 2025
