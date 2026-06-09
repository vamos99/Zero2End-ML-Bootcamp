# Olist Intelligence Suite

Olist e-ticaret veri seti ile hazırlanmış analitik dashboard ve ML workflow prototipi. Proje; veri hazırlama, SQL ile yeniden kullanılabilir metrik mantığı, tahmin servisleri ve teknik olmayan kullanıcı için karar odaklı dashboard anlatımını bir araya getirir.

> [!NOTE]
> Bu proje, **Zero2End ML Bootcamp** bitirme projesi kapsamında verilen talimatlara uygun olarak hazırlanmıştır.
> 📄 [Bootcamp Proje Talimatlarını İncele (PDF)](docs/reports/Zero2End_ML_Bootcamp_Project_Report.pdf)

## Proje Kapsamı ve Mevcut Durum

Proje bootcamp bitirme kapsamını karşılar; production seviyesinde servis veya canlı veri platformu iddiası taşımaz. Dashboard, Kaggle verisi, model çıktıları ve ortam değişkenleri hazır olduğunda anlamlıdır.

| Gereksinim | Durum | Uygulama Detayı |
|------------|-------|-----------------|
| **Veri Analizi (EDA)** | Uygulandı | Notebook 1'de veri keşfi ve hazırlık adımları yer alır. |
| **Model Geliştirme** | Prototip | CatBoost (lojistik/churn) ve SVD öneri yaklaşımı notebook ve `src/ml/` altında tutulur. |
| **Pipeline Kurulumu** | Yerel akış | Kaggle CSV -> SQLite/Postgres uyumlu tablo akışı `ingest.py` ile hazırlanmıştır. |
| **Dashboard** | Ortam bağımlı | Streamlit dashboard yerel veritabanı ve üretilmiş tahmin/segment tabloları hazırsa dolu çalışır. |
| **Kod Kalitesi** | Geliştiriliyor | `src/` modüler yapı, testler, schema contract ve SQL reconciliation kontrolleri vardır. |
| **Raporlama** | Geliştiriliyor | README, notebook açıklamaları, SQL metric docs ve PM/backlog notları birlikte tutulur. |
| **Analitik SQL Katmanı** | Eklendi | `sql/views/` altında dashboard ve veri modeli için tekrar kullanılabilir view örnekleri. |


| **Ana Sayfa (Dashboard)** | **Operasyon Merkezi** |
|:---:|:---:|
| ![Ana Sayfa](docs/assets/img/dashboard_home.png) | ![Operasyon](docs/assets/img/operations_overview.png) |

| **Müşteri Sadakati (Retention)** | **Segmentasyon Analizi** |
|:---:|:---:|
| ![Sadakat](docs/assets/img/customer_loyalty_overview.png) | ![Segmentasyon](docs/assets/img/segmentation_overview.png) |

| **Ranking & Trends** | **Ürün Öneri Motoru** |
|:---:|:---:|
| ![Ranking](docs/assets/img/ranking_top_categories_revenue.png) | ![Öneri](docs/assets/img/customer_loyalty_recommendations.png) |

---

## Problem & Çözüm

### Problem 1: Teslimat Gecikmesi
**Sorun:** Müşteriler siparişlerin ne zaman geleceğini bilemiyor, gecikmeler şikayete dönüşüyor.  
**Çözüm:** CatBoost modeli ile teslimat süresi tahmini prototipi. Notebook çıktılarında yaklaşık 7.6 gün RMSE raporlanmıştır; bu değer raw veriyle yeniden çalıştırılarak doğrulanmalıdır.

**Neden Bu Yaklaşım?**
*   Haversine mesafe (satıcı-müşteri arası) en önemli faktör
*   Satıcı puanı (review verisi) teslimat performansıyla ilişkili
*   Aynı eyalet = daha hızlı teslimat

### Problem 2: Müşteri Kaybı (Churn)
**Sorun:** Hangi müşterilerin platformu terk edeceğini önceden tahmin edemiyoruz.  
**Tanım Nedir?:** *Churn*, bir müşterinin platformu kullanmayı bırakması (terk etmesi) demektir.  
**Bizdeki Karşılığı:** 90 gün boyunca hiç sipariş vermeyen müşteri, analizde **riskli/kaybedilmiş** olarak etiketlenir.
**Çözüm:** CatBoost Classifier ile churn risk prototipi. Bu bölüm production churn modeli değil, metodoloji ve dashboard anlatımı için kullanılan bir deneydir.

**Neden Bu Yaklaşım?**
*   `customer_unique_id`, tekrar satın alma ve retention analizinde `customer_id`'den daha anlamlıdır
*   90 gün kuralı pratik bir risk tanımıdır; zaman bazlı train/test ayrımıyla yeniden doğrulanmalıdır
*   Mevcut feature/target tasarımı target-proxy riski taşıdığı için model sonuçları dikkatli yorumlanmalıdır

### Problem 3: Müşteri Tek Tip Görülüyor
**Sorun:** Tüm müşterilere aynı pazarlama yapılıyor.  
**Çözüm:** RFM + K-Means ile segmentasyon (5 segment)

## Analytics & Data Engineering Açısı

Bu proje production seviyesinde bir veri platformu iddiası taşımaz; bootcamp kapsamındaki veri setini daha okunabilir bir analitik ürüne dönüştürmeyi hedefler.

| Katman | Bu Projede Karşılığı |
|--------|-----------------------|
| **Raw data** | Kaggle Olist CSV dosyaları (`data/raw`, Git'e dahil değil) |
| **Ingestion** | `src/ml/ingest.py` ile CSV -> SQLite/Postgres uyumlu tablo akışı |
| **Analytics model** | `sql/views/` altında revenue, delivery quality, seller performance ve segment view'ları |
| **ML workflow** | Notebooklar ve `src/ml/` altında lojistik, churn ve öneri prototipleri |
| **Serving** | FastAPI endpointleri ve Streamlit dashboard |
| **Quality checks** | Pytest, schema contract, data-quality checks ve GitHub Actions CI |

### SQL View'ları

SQL dosyaları, dashboard metriklerinin nasıl yeniden kullanılabilir analitik çıktılara çevrilebileceğini göstermek için eklendi.

```bash
python scripts/apply_sql_views.py
```

Bu komut, lokal `olist.db` veya `DATABASE_URL` ile tanımlanmış veritabanı üzerinde `sql/views/` altındaki view'ları uygular.

Veri ve tablo kalitesini kontrol etmek için:

```bash
python scripts/validate_olist_schema.py --target csv
python scripts/validate_olist_schema.py --target db
python scripts/validate_olist_schema.py --target quality
```

Raw CSV veya `olist.db` yoksa bu komutların fail vermesi beklenen davranıştır; önce Kaggle verisi indirilip ingest akışı çalıştırılmalıdır.

---

## Teknoloji Tercihleri

| Teknoloji | Neden? |
|-----------|--------|
| **SQLite** | Local geliştirme ve taşınabilirlik için ideal (Konfigürasyon gerektirmez) |
| **SQL Views** | Dashboard metriklerini notebook dışına çıkarıp tekrar kullanılabilir hale getirir |
| **Streamlit** | Dashboard prototipini hızlı ve okunabilir şekilde sunar |
| **Docker** | "Benim bilgisayarımda çalışıyordu" problemini çözer |
| **Polars** | CSV okuma/yazma tarafında hızlı ve pratik alternatif |
| **FastAPI** | Modern, async, otomatik dokümantasyon (Backend API) |

---

## Özellikler

### Lojistik Tahmin
*   **RMSE:** Notebook çıktısında yaklaşık 7.60 gün
*   **Özellikler:** Mesafe, kargo, fiyat, ağırlık, satıcı puanı

### Churn Tahmini
*   **Tanım:** 90 gün sipariş yok = churn/risk etiketi
*   **Not:** Bu bölüm predictive model iddiasından çok risk skoru ve metodoloji prototipi olarak okunmalıdır

### Müşteri Segmentasyonu
*   **5 Segment:** Şampiyonlar, Sadıklar, Potansiyeller, Riskli, Uyuyanlar

### Dashboard
*   **5 Sayfa:** Executive overview, Operasyon, Müşteri, Segmentasyon, Ranking
*   **ROI Simülasyonu:** Kampanya maliyet/getiri analizi

### API
*   **4 Endpoint:** `/predict/delivery`, `/predict/churn`, `/recommend`, `/segments`
*   **Güvenlik:** X-API-KEY koruması

### Data Quality
*   **Schema contract:** Kaggle Olist'in 9 CSV / 52 kolon beklentisi `src/data_contract.py` altında tanımlıdır.
*   **DB kalite kontrolleri:** Boş tablo, duplicate key, orphan foreign key, kabul edilen status/payment değerleri, negatif ödeme/fiyat ve imkansız teslimat tarihleri kontrol edilir.

---

## 🚀 Kurulum ve Çalıştırma

Proje hem Yerel (Local) hem de Docker ortamında çalışacak şekilde tasarlanmıştır.

### Ön Gereksinimler
*   Docker & Docker Compose (Önerilen)
*   Git
*   Python 3.10+ (Yerel çalışma için)

### Adım 1: Projeyi İndir
```bash
git clone https://github.com/vamos99/Zero2End-ML-Bootcamp.git
```

### Adım 2: Python Ortamını Kurun (Sadece Yerel Çalışma İçin)
Projenin bağımlılıklarını izole etmek için sanal ortam kurmanız önerilir:

```bash
# Sanal Ortam Oluştur
python -m venv venv

# Aktif Et (Mac/Linux)
source venv/bin/activate
# Aktif Et (Windows)
# .\venv\Scripts\activate

# Kütüphaneleri Yükle
pip install -r requirements.txt

# Kernel'i Notebook'a Tanıt (ÖNEMLİ)
python -m ipykernel install --user --name=venv --display-name "Python (Olist Project)"
```

### Adım 3: Ortam Değişkenlerini Ayarla (.env)
Projenin çalışması için bir `.env` dosyası oluşturun (Örnek dosyadan kopyalayabilirsiniz). Notebooklar ve Docker bu dosyayı kullanır.

```bash
# MacOS/Linux
cp .env.example .env
# Windows
copy .env.example .env
```
Ardından `.env` dosyasını açıp **KAGGLE_USERNAME** ve **KAGGLE_KEY** bilgilerinizi ekleyin (Veri indirmek için gereklidir).

### Adım 4: Veri Hazırlığı ve Modeller
Proje açıldığında API çalışır (`.pkl` modelleri hazır gelir). Ancak **Dashboard grafiklerinin** dolması için geçmiş tahminlerin üretilmesi gerekir.

**Sırayla Çalıştırın:**
1.  `notebooks/1_general_eda_and_prep.ipynb`: **(Zorunlu)** Veritabanı boşsa [Kaggle Olist Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) verisini indirir ve SQL tablolarını kurar.
2.  `notebooks/2_logistics_engine.ipynb`: **(Gerekli)** Dashboard'daki "Operasyon" ekranının dolması için lojistik tahminlerini veritabanına yazar.
3.  `notebooks/3_customer_sentinel.ipynb`: **(Gerekli)** Churn modelini eğitir ve analiz eder.
4.  `notebooks/4_growth_engine.ipynb`: **(Gerekli)** Dashboard'daki "Müşteri" ekranının dolması için segmentasyon verilerini veritabanına yazar.

**İsteğe Bağlı Analizler (Opsiyonel):**
*   `notebooks/5_final_evaluation.ipynb`: Tüm modellerin toplu performans karşılaştırması.
*   `notebooks/6_executive_pipeline.ipynb`: Yeni gelen haftalık verinin nasıl işleneceğini simüle eden pipeline.
*Not: Veritabanı (`olist.db`) bu işlem sonunda dolacaktır.*

### Seçenek A: Docker ile Başlatma (Önerilen)
Tüm servisleri (API, Dashboard, MLflow) tek komutla başlatın.

```bash
docker-compose up --build
```

### Seçenek B: Hızlı Başlangıç (Script ile)
Tek komutla MLflow, API ve Dashboard'u aynı anda başlatın:

```bash
chmod +x run_local.sh
./run_local.sh
```

### Seçenek C: Manuel (Adım Adım)
Eğer her servisi ayrı terminalde görmek isterseniz:

1. **Terminal 1: MLflow Arayüzü (Zorunlu)**
   ```bash
   mlflow ui --port 5000
   ```
   *(Bunu başlatmazsanız API modelleri yükleyemez ve açılmaz)*

2. **Terminal 2: API**
   ```bash
   uvicorn src.app:app --reload
   ```

3. **Terminal 3: Dashboard**
   ```bash
   streamlit run src/dashboard.py
   ```

---

## Notebook'ları Çalıştırma (Geliştirme)

Analiz yapmak için yerel Python ortamınıza bağımlılıkları yüklediğinizden emin olun (Adım 2'deki gibi).
Notebooklar `.env` dosyasındaki ayarları otomatik okur.

```bash
cd notebooks
jupyter lab
```

---

## Dosya Yapısı

```
src/
├── app.py          # FastAPI Backend
├── dashboard.py    # Streamlit Frontend
├── ml/             # ML Core (Eğitim, Ingestion)
│   ├── ingest.py   # CSV → SQLite
│   └── train.py    # Model Eğitimi
├── services/       # İş Mantığı (Service Layer)
├── views/          # Dashboard Sayfaları
└── database/       # Veritabanı Bağlantısı

notebooks/
├── 1_general_eda_and_prep.ipynb  # Veri keşfi ve Yükleme
├── 2_logistics_engine.ipynb      # Teslimat modeli eğitimi
├── 3_customer_sentinel.ipynb     # Churn analizi
├── 4_growth_engine.ipynb         # Segmentasyon modeli
└── ...

data/               # CSV dosyaları (Git-ignored)
models/             # Eğitilmiş modeller (.pkl)
docs/               # Proje dökümanları ve görseller
sql/views/          # Analitik SQL view örnekleri
scripts/            # Lokal yardımcı scriptler
```

## Model Performansı ve Notlar

| Model | Algoritma | Metrik | Değer |
|-------|-----------|--------|-------|
| **Lojistik** | CatBoost Regressor | RMSE | Notebook çıktısında ~7.6 gün |
| **Churn** | CatBoost Classifier | Accuracy | Notebook çıktısı; imbalanced veri ve target-proxy riskiyle yorumlanmalı |
| **Recommender** | SVD | Coverage | Notebook çıktısı; cold-start/evaluation detayları sınırlı |

Bu değerler portföy/prototip bağlamında tutulur. Raw Kaggle verisi ve yerel `olist.db`
ile yeniden çalıştırılmadan güncel model performansı olarak sunulmamalıdır.

---

### Troubleshooting (Sorun Giderme)

*   **API Bağlantı Hatası:** MacOS kullanıcıları `localhost` yerine `127.0.0.1` kullanmalıdır (Projede varsayılan olarak ayarlanmıştır).
*   **Grafikler/Tablolar Boş Görünüyor:**
    *   **Durum:** API ve Simülasyonlar çalışıyor (`.pkl` modelleri hazır geldiği için).
    *   **Çözüm:** Dashboard'daki *"Operasyon Merkezi"* ve segmentasyon ekranlarının dolması için veritabanında tahmin/segment tablolarının oluşması şarttır. Bunu sağlamak için **Notebook 2 (Lojistik)** ve **Notebook 4 (Growth/Segmentasyon)** dosyalarını bir kez çalıştırmanız gerekir.
*   **Docker Port Hatası:** Yerelde çalışan servisleri (`Ctrl+C`) kapatıp `docker-compose`'u yeniden başlatın.

---
**Versiyon:** 2.2 | **Güncelleme:** Haziran 2026
