# Olist Intelligence Suite 🚀

**Olist Intelligence Suite**, Brezilya'nın en büyük e-ticaret platformlarından biri olan Olist'in verilerini kullanarak geliştirilmiş, uçtan uca (End-to-End) bir Veri Bilimi ve İş Zekası çözümüdür.

Bu proje, sadece model eğitmekle kalmayıp, bu modelleri **canlı bir ürüne** dönüştürerek iş birimlerinin (Operasyon, Pazarlama) aksiyon almasını sağlar.

---

## 🌟 Özellikler

### 1. 📦 Operasyon Merkezi (Logistics Engine)
*   **Sorun:** Siparişlerin gecikip gecikmeyeceğini önceden tahmin eder.
*   **Çözüm:** Makine Öğrenmesi (CatBoost) ile teslimat süresi tahmini.
*   **Aksiyon:** Gecikme riski olan siparişler için otomatik uyarı sistemi ve e-posta simülasyonu.
*   **KPI:** Zamanında Teslimat Oranı, Ortalama Teslimat Süresi, Şikayet Riski.

### 2. 🤝 Müşteri Sadakati (Customer Retention)
*   **Sorun:** Müşterilerin platformu terk etmesini (Churn) önlemek.
*   **Çözüm:** RFM analizi ve Churn tahminlemesi.
*   **Aksiyon:** Riskli müşteriler için "İndirim Tanımla" veya "Puan Yükle" gibi senaryoların ROI (Yatırım Getirisi) simülasyonu.

### 3. 📊 Segmentasyon Analizi (Growth Engine)
*   **Sorun:** Müşterileri tek tip görmek yerine davranışlarına göre gruplamak.
*   **Çözüm:** K-Means Kümeleme ile müşteri segmentasyonu (Şampiyonlar, Sadıklar, Uyuyanlar).
*   **Aksiyon:** Her segmente özel pazarlama stratejisi önerileri.

---

## 🏗️ Mimari (Architecture)

Proje, modern yazılım geliştirme prensiplerine (**Clean Architecture**, **MVC**) uygun olarak tasarlanmıştır:

*   **Data Layer (`src/database/`):** PostgreSQL ile konuşan, ham SQL sorgularını barındıran katman.
*   **Service Layer (`src/services/`):** İş mantığını (Business Logic), hesaplamaları ve veri maskelemeyi yöneten katman.
*   **View Layer (`src/views/`):** Streamlit ile kullanıcı arayüzünü oluşturan katman.
*   **Controller (`src/dashboard.py`):** Tüm akışı yöneten ana kontrolcü.

### Teknoloji Yığını (Tech Stack)
*   **Backend:** Python 3.10, FastAPI
*   **Frontend:** Streamlit
*   **Database:** PostgreSQL 15
*   **MLops:** MLflow, Docker, Docker Compose
*   **Data Processing:** Polars (ETL), Pandas (Dashboard)

---

## 🧠 Neden Bu Teknolojileri Seçtik? (Design Decisions)

Projede kullanılan her teknolojinin belirli bir amacı vardır:

### 1. Polars vs Pandas 🐼 vs 🐻‍❄️
*   **Polars:** Büyük veri setlerini (ETL aşaması) işlemek için kullanıldı. Pandas'a göre çok daha hızlıdır ve bellek dostudur. `src/ingest.py` ve Notebook'larda ana işleyicidir.
*   **Pandas:** Dashboard tarafında kullanıldı. Streamlit ve Plotly kütüphaneleri Pandas ile %100 uyumlu çalıştığı için, sunum katmanında Pandas'ın esnekliğinden faydalandık.

### 2. Neden PostgreSQL? 🐘
*   SQLite gibi dosya tabanlı sistemler "Production" ortamında (özellikle Docker içinde) kilitlenme (lock) ve izin sorunları yaşatır.
*   PostgreSQL, çoklu kullanıcı desteği ve veri bütünlüğü ile gerçek bir kurumsal çözümdür.

### 3. Neden Streamlit? 🎈
*   React veya Vue gibi frontend framework'leri ile aylar sürecek geliştirme sürecini günlere indirmek için.
*   Veri Bilimcilerin kendi araçlarını (Python) kullanarak hızlıca prototip ve ürün geliştirmesini sağlar.

### 4. Neden Docker? 🐳
*   "Benim bilgisayarımda çalışıyordu" sorununu tarihe gömmek için.
*   Tüm bağımlılıkları (Python, DB, MLflow) tek bir paket halinde sunarak kurulumu standartlaştırmak için.

---

## 🚀 Kurulum (Installation)

Proje tamamen **Docker** üzerinde çalışacak şekilde yapılandırılmıştır. Bilgisayarınızda Docker ve Docker Compose yüklü olması yeterlidir.

### 1. Repoyu Klonlayın
```bash
git clone https://github.com/kullaniciadi/olist-intelligence.git
cd olist-intelligence
```

### 2. Sistemi Başlatın
Tek bir komutla tüm servisleri (API, Dashboard, DB, MLflow) ayağa kaldırın:
```bash
docker-compose up --build
```
*(İlk kurulumda imajların indirilmesi ve veritabanının hazırlanması birkaç dakika sürebilir.)*

### 3. Uygulamaya Erişin
*   **Dashboard:** [http://localhost:8501](http://localhost:8501)
*   **API Dokümantasyonu:** [http://localhost:8000/docs](http://localhost:8000/docs)
*   **MLflow UI:** [http://localhost:5000](http://localhost:5000)

---

## 📂 Dosya Yapısı

```
olist-intelligence/
├── docker-compose.yml      # Servis orkestrasyonu
├── Dockerfile              # Python ortamı
├── requirements.txt        # Kütüphane bağımlılıkları
├── src/
│   ├── app.py              # FastAPI uygulaması
│   ├── dashboard.py        # Ana Dashboard (Controller)
│   ├── config.py           # Ayarlar
│   ├── database/           # Veritabanı kodları
│   ├── services/           # İş mantığı
│   └── views/              # Ekran tasarımları
└── notebooks/              # Model eğitim not defterleri
```

---

## 🛡️ Lisans
Bu proje Zero2End ML Bootcamp kapsamında eğitim amaçlı hazırlanmıştır.
