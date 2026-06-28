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

## Open Source Maintenance

This repository is maintained as a public, reviewable reference project for analytics engineering and applied ML workflow design. The current maintenance focus is not to present a production platform, but to keep the project understandable, reproducible, and useful for students or early-career developers studying data applications.

Current maintenance areas:

- issue triage and small pull-request workflow;
- documentation, setup, and validation cleanup;
- SQL view and dashboard/API contract consistency;
- schema validation and data-quality checks;
- test coverage for behavior that does not require local raw data;
- transparent notes on model, data, and demo limitations.

Contributions are welcome when they keep the project small, reproducible, and clearly validated. See [`CONTRIBUTING.md`](CONTRIBUTING.md), [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md), and [`LICENSE`](LICENSE).

---

## Hızlı Erişim

- **Proje Talimatları:** [PDF](olist-intelligence/docs/reports/Zero2End_ML_Bootcamp_Project_Report.pdf)
- **Demo notu:** Dashboard yerel veri, model çıktıları ve ortam değişkenleri hazır olduğunda dolu çalışır.
- **Detaylı Dökümantasyon:** [Olist Intelligence README](olist-intelligence/README.md)
- **Mimari / Akış:** [Olist Mimari Notları](docs/architecture.md)
- **Proje Yönetimi:** [Olist Analytics Board](https://github.com/users/vamos99/projects/3) / [Proje Yönetimi Notları](docs/project-management.md)
- **Katkı Rehberi:** [CONTRIBUTING.md](CONTRIBUTING.md)
- **Davranış Kuralları:** [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- **Lisans:** [MIT License](LICENSE)

---

**Geliştirici:** Halil Kıyak  
**Tarih:** Aralık 2025  
**Son bakım:** Haziran 2026
