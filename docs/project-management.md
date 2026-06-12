# Proje Yönetimi

Bu dosya, Olist Intelligence için GitHub Projects board'un nasıl kullanılacağını kısa şekilde açıklar. Ana takip yeri bu markdown dosyası değil, GitHub Project board'dur.

## GitHub Project

- Board: [Olist Analytics Board](https://github.com/users/vamos99/projects/3)
- Durum: public
- Amaç: Olist projesindeki küçük ve takip edilebilir işleri issue/PR akışıyla yönetmek.

## Board Alanları

| Alan | Değerler |
| --- | --- |
| Status | Backlog, Ready, In Progress, Review, Done |
| Priority | P0, P1, P2 |
| Area | analytics, dashboard, data-pipeline, ml, docs, ci, api |
| Size | S, M, L |
| Sprint | Stabilization, Validation, Enhancement |

## Kullanım Akışı

1. Yeni iş önce issue olarak açılır.
2. Kapsam netleşince Ready durumuna alınır.
3. Kod veya doküman değişikliği ayrı branch'te yapılır.
4. Her branch tek amaçlı tutulur; alakasız işler aynı PR'a eklenmez.
5. PR açılınca issue Review durumuna taşınır.
6. PR merge edilince issue Done olur.
7. Yeni özelliklere geçmeden önce açık bug, validation ve dokümantasyon işleri kapatılır.

## Issue Hazırlık Kriteri

- Kullanıcıya, dashboard'a veya veri doğruluğuna etkisi bir cümleyle yazılmış olmalı.
- Kullanılacak veri kaynağı, tablo veya endpoint belirtilmeli.
- Kabul kriterinde en az bir doğrulama adımı olmalı.
- Secret, özel veri veya deployment varsayımı varsa açıkça yazılmalı.
- Algoritma denemesi ise önce hipotez ve ölçüm metriği belirtilmeli.

## Done Kriteri

- Değişiklik feature branch üzerinde commitlenmiş olmalı.
- İlgili test, validation veya doküman kontrolü tanımlanmış olmalı.
- SQL, dashboard veya API davranışı değiştiyse ilgili doküman güncellenmiş olmalı.
- PR açıklaması ne değiştiğini ve nasıl doğrulandığını kısa anlatmalı.
- Büyük refactor ayrı issue olarak açılmalı.

## Aktif İş Havuzu

Bu tablo board'un yerini almaz; sadece README ve PR planı yazarken kısa referans olarak tutulur.

| Öncelik | Alan | İş | Kabul kriteri |
| --- | --- | --- | --- |
| P1 | data-pipeline | Yüklenen Olist CSV paketini schema contract ile doğrula | Dosya ve kolon sözleşmesi doğrulanır, raw veri repo'ya eklenmez. |
| P1 | docs | README komutlarını mevcut kod akışıyla karşılaştır | Kurulum, veri hazırlama ve validation komutları kodla uyumlu hale getirilir. |
| P2 | ml | Delivery/churn model card ekle | Amaç, özellikler, sınırlılıklar, leakage riski ve doğrulama notları yazılır. |
| P2 | refactor | src/database/repository.py için bölme planı çıkar | Fonksiyon grupları belirlenir; davranış değiştirmeyen küçük PR'lara ayrılır. |
| P2 | docs | Dashboard ekran görüntülerini yenile | Sadece yerel veri ve browser QA sonrası eklenir. |

## Tamamlanan Son İşler

| Alan | İş | Kanıt |
| --- | --- | --- |
| dashboard/api | Recommendation client payload düzeltmesi | PR #19 |
| api | Protected inference endpoint API key düzeltmesi | PR #23 |
| analytics | Executive KPI metric dictionary | olist-intelligence/sql/METRICS.md |
| data-pipeline | Kaggle source schema contract | olist-intelligence/src/data_contract.py |
| data-pipeline | DB kalite kontrolleri | olist-intelligence/tests/test_data_contract.py |
| analytics | Payment, review-delivery ve seller SLA marts | olist-intelligence/sql/views/ |
| analytics | Cohort/retention mart | olist-intelligence/sql/views/customer_cohort_retention.sql |
| dashboard | Executive dashboard SQL mart eşlemesi | olist-intelligence/src/views/home_view.py |
| ci | Küçük SQLite fixture testleri | olist-intelligence/tests/ |

## Label Önerisi

- type: task, type: bug, type: docs, type: refactor, type: experiment
- area: analytics, area: dashboard, area: data-pipeline, area: ml, area: api, area: ci, area: docs
- priority: P0, priority: P1, priority: P2

## Veri Yönetimi Notu

Olist CSV dosyaları repo'ya commitlenmez. Yüklenen arşiv yalnızca local schema doğrulama, data-quality kontrolü ve dokümantasyon tutarlılığı için referans olarak kullanılır.
