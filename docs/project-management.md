# Proje Yönetimi

Bu dosya, Olist Intelligence için GitHub Projects board'un nasıl kullanılacağını
kısa şekilde açıklar. Ana takip yeri bu markdown dosyası değil, GitHub Project
board'dur.

## GitHub Project

- Board: [Olist Analytics Board](https://github.com/users/vamos99/projects/3)
- Durum: public
- Amaç: Olist projesindeki küçük ve takip edilebilir işleri issue/PR akışıyla
  yönetmek.

## Board Alanları

| Alan | Değerler |
| --- | --- |
| Status | Backlog, Ready, In Progress, Review, Done |
| Priority | P0, P1, P2 |
| Area | analytics, dashboard, data-pipeline, ml, docs, ci |
| Size | S, M, L |
| Sprint | Sprint 1, Sprint 2, Sprint 3 |

## Kullanım Akışı

1. Yeni fikir önce GitHub Project board'da Backlog olarak açılır.
2. Kapsam netleşince issue Ready durumuna alınır.
3. Kod veya doküman değişikliği ayrı branch'te yapılır.
4. PR açılınca issue Review durumuna taşınır.
5. CI geçip PR merge edilince issue Done olur.

## Issue Hazırlık Kriteri

- Kullanıcıya veya analize etkisi bir cümleyle yazılmış olmalı.
- Kullanılacak veri kaynağı ve metrik grain'i belirtilmeli.
- Kabul kriterinde en az bir doğrulama adımı olmalı.
- Secret, özel veri veya deployment varsayımı varsa açıkça yazılmalı.

## Done Kriteri

- Değişiklik feature branch üzerinde commitlenmiş olmalı.
- İlgili test, validation veya doküman kontrolü çalışmış olmalı.
- SQL/dashboard sonucu seçilen veri kaynağıyla tutarlı olmalı.
- README, SQL docs veya runbook davranış değiştiyse güncellenmiş olmalı.
- PR açıklaması ne değiştiğini ve nasıl doğrulandığını kısa anlatmalı.

## Aktif İş Havuzu

Bu tablo board'un yerini almaz; sadece README ve PR planı yazarken kısa referans
olarak tutulur.

| Öncelik | Alan | İş | Kabul kriteri |
| --- | --- | --- | --- |
| P1 | dashboard | Dashboard chart -> SQL mart eşlemesini dokümante et | Ana chart'ların hangi view'dan beslendiği README veya docs içinde görünür. |
| P2 | ml | Delivery/churn model card ekle | Amaç, özellikler, sınırlılıklar, veri sızıntısı riski ve doğrulama notları yazılır. |
| P2 | docs | Dashboard ekran görüntülerini yenile | Sadece yerel veri ve Browser QA sonrası eklenir. |

## Tamamlanan Son İşler

| Alan | İş | Kanıt |
| --- | --- | --- |
| analytics | Executive KPI metric dictionary | `olist-intelligence/sql/METRICS.md` |
| data-pipeline | Kaggle source schema contract | `olist-intelligence/src/data_contract.py` |
| data-pipeline | DB kalite kontrolleri | `olist-intelligence/tests/test_data_contract.py` |
| analytics | Payment, review-delivery ve seller SLA marts | `olist-intelligence/sql/views/`, `tests/test_sql_views.py` |
| analytics | Cohort/retention mart | `olist-intelligence/sql/views/customer_cohort_retention.sql`, `tests/test_sql_views.py` |
| ci | Küçük SQLite fixture testleri | `olist-intelligence/tests/` |

## Label Önerisi

- `type: task`, `type: bug`, `type: docs`
- `area: analytics`, `area: dashboard`, `area: data-pipeline`, `area: ml`, `area: ci`
- `priority: P0`, `priority: P1`, `priority: P2`
