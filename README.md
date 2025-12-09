# Zero2End ML Bootcamp: Olist Intelligence Suite 🚀
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://zero2end-ml-bootcamp.streamlit.app/)

**Veri Odaklı E-Ticaret Yönetim Platformu**  
Brezilya'nın en büyük pazaryeri Olist'in 100.000+ sipariş verisi ile eğitilmiş; Lojistik, CRM ve Satış operasyonlarını optimize eden Yapay Zeka destekli karar destek sistemi.

---

### 📑 [Proje Raporunu İndir (PDF)](./olist-intelligence/docs/reports/Zero2End_ML_Bootcamp_Project_Report.pdf)
Detaylı model metodolojisi, iş problemi analizi ve teknik mimariyi içeren kapsamlı rapor.

---

## 📸 Uygulama Önizleme (Dashboard)

**Proje Canlıda!** Yukarıdaki butona tıklayarak uygulamayı deneyimleyebilirsiniz.

| **Operasyon Merkezi (Lojistik)** | **Müşteri Segmentasyonu (CRM)** |
|:---:|:---:|
| ![Operasyon](olist-intelligence/docs/assets/img/operations_overview.png) | ![Segmentasyon](olist-intelligence/docs/assets/img/segmentation_overview.png) |
| *Teslimat gecikmelerini %90 doğrulukla öngören erken uyarı sistemi.* | *RFM analizi ile müşteri tabanını 5 stratejik segmente ayıran modül.* |

| **Ranking & Trendler** | **Akıllı Ürün Önerisi** |
|:---:|:---:|
| ![Ranking](olist-intelligence/docs/assets/img/ranking_top_categories_revenue.png) | ![Öneri](olist-intelligence/docs/assets/img/customer_loyalty_recommendations.png) |
| *Gelir ve satış bazlı dinamik performans takibi.* | *Kullanıcı bazlı (SVD) kişiselleştirilmiş ürün öneri motoru.* |

---

## 🎯 Projenin Amacı ve Çözümler

Bu proje, bir E-Ticaret firmasının karşılaşabileceği 3 ana darboğaza Makine Öğrenmesi ile çözüm üretir:

### 1. 🚚 Lojistik Optimizasyonu (Tahminleme)
*   **Sorun:** Müşteriye söz verilen teslimat tarihi ile gerçekleşen tarih arasındaki sapmalar.
*   **Çözüm:** **CatBoost Regressor** kullanarak sipariş anında teslimat süresini ve gecikme riskini tahmin eder.
*   **Değer:** Müşteri şikayetlerini proaktif olarak önleme ve kargo süreçlerini denetleme imkanı.

### 2. 💔 Müşteri Terk (Churn) Analizi
*   **Sorun:** Hangi müşterinin platformu bırakacağını bilememek.
*   **Çözüm:** Sipariş sıklığı ve parasal değeri analiz eden **Churn Prediction** modeli.
*   **Değer:** Riskli müşterilere (Churn ihtimali > %70) otomatik kampanya önerileri sunarak sadakati artırma.

### 3. 👥 Müşteri Segmentasyonu (K-Means)
*   **Sorun:** Her müşteriye aynı iletişim dilini kullanmak.
*   **Çözüm:** Müşterileri "Şampiyonlar", "Sadıklar", "Riskli" gibi 5 sınıfa ayıran yapay zeka kümelemesi.
*   **Değer:** Pazarlama bütçesini doğru kitleye (Target Audience) harcama yeteneği.

---

## 🛠️ Kullanılan Teknolojiler

| Alan | Teknoloji | Kullanım |
|------|-----------|----------|
| **Frontend** | Streamlit | İnteraktif Dashboard ve Kullanıcı Arayüzü |
| **Backend** | Python (FastAPI) | Model servisleri ve iş mantığı |
| **Database** | SQLite / PostgreSQL | Veri saklama ve sorgulama |
| **ML Core** | CatBoost, Scikit-learn | Model eğitimi ve tahminleme |
| **Data Eng** | Polars, SQL | Yüksek performanslı veri işleme (ETL) |
| **Ops** | Docker | Konteynerizasyon ve dağıtım |

---

## 📂 Dosya Yapısı ve Kurulum

Projenin kaynak kodları, notebooklar ve teknik dokümantasyon `olist-intelligence` klasöründedir.

👉 **[KAYNAK KODLARI VE KURULUM REHBERİ İÇİN TIKLAYIN](./olist-intelligence/README.md)**

---
*Geliştirici: Halil Kıyak | Zero2End ML Bootcamp Capstone Project © 2025*
