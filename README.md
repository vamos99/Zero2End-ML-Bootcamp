# Zero2End ML Bootcamp - Final Project

**Zero2End ML Bootcamp** bitirme projesi için hazırlanmış e-ticaret analitiği ve ML workflow çalışmasıdır. Proje, Olist veri seti üzerinden dashboard, SQL tabanlı analitik modelleme, tahminleme ve basit aksiyon simülasyonlarını bir araya getirir.

## Proje İçeriği

Bu depo, uçtan uca geliştirilmiş bir e-ticaret iş zekası ve tahminleme prototipini içerir. Odak noktası üretim seviyesi bir platform iddiası değil; veri hazırlama, analitik çıktı üretme, dashboard ile anlatma ve ML modellerini servis edilebilir hale getirme pratiğidir.

### [Olist Intelligence Suite](olist-intelligence/)

Tüm kaynak kodlar, notebooklar ve dökümantasyon **`olist-intelligence/`** klasörü altındadır.

- **Executive dashboard:** teknik olmayan kullanıcı için özet metrikler ve yönlendirici grafikler.
- **SQL analytics layer:** SQLite/Postgres uyumlu view dosyaları ile tekrar kullanılabilir metrik mantığı.
- **Data quality:** Kaggle source contract, schema validation ve DB kalite kontrolleri.
- **Lojistik tahmin modülü:** teslimat süresi ve gecikme riski.
- **Müşteri analitiği:** RFM segmentasyon, churn riski ve hedef kitle çıktısı.
- **Recommendation prototype:** ürün öneri akışı.

---

## Hızlı Erişim

- **Proje Talimatları:** [PDF](olist-intelligence/docs/reports/Zero2End_ML_Bootcamp_Project_Report.pdf)
- **Demo notu:** Dashboard yerel veri, model çıktıları ve ortam değişkenleri hazır olduğunda dolu çalışır.
- **Detaylı Dökümantasyon:** [Olist Intelligence README](olist-intelligence/README.md)
- **Mimari / Akış:** [Project Architecture](docs/architecture.md)
- **Proje Yönetimi:** [Live Project Board](https://github.com/users/vamos99/projects/3) / [Backlog Guide](docs/project-management.md)

---
**Geliştirici:** Halil Kıyak
**Tarih:** Aralık 2025
**Son bakım:** Haziran 2026
