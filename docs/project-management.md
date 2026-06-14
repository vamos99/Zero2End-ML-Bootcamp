# Proje Yönetimi

Bu dosya, Olist Intelligence için GitHub Projects board'un nasıl kullanılacağını kısa şekilde açıklar. Ana takip yeri bu markdown dosyası değil, GitHub Project board'dur.

## GitHub Project

- Board: [Olist Analytics Board](https://github.com/users/vamos99/projects/3)
- Durum: public
- Amaç: Olist projesindeki küçük ve takip edilebilir işleri issue/PR akışıyla yönetmek.

## Board Alanları

| Alan | Değerler |
| --- | --- |
| Status | Todo, In Progress, Done |
| Labels | İş türü ve alanı issue/PR etiketleriyle belirtilir |
| Linked pull requests | Uygulama PR'ı board item ile ilişkilendirilir |

Board küçük tutulduğu için ayrı Priority, Area, Size ve Sprint alanları
eklenmemiştir. Öncelik ve alan gerektiğinde label ile belirtilir.

## Kullanım Akışı

1. Yeni iş önce issue olarak açılır.
2. Kapsam netleşince Todo durumunda tutulur.
3. Kod veya doküman değişikliği ayrı branch'te yapılır ve In Progress olur.
4. Her branch tek amaçlı tutulur; alakasız işler aynı PR'a eklenmez.
5. PR açılınca linked pull request alanı kullanılır.
6. PR ve CI tamamlanıp merge edilince issue Done olur.
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
| docs | Dataset, architecture ve roadmap baseline | PR #42 |
| refactor | Repository helper integration batch 2 | PR #43 |
| refactor | Ranking repository behavior | PR #44 |
| refactor | Ranking domain split ve compatibility wrappers | PR #45 |
| refactor | Action domain split ve bounded limit | PR #46 |

## Label Kullanımı

- Tür: `refactor`, `docs`, `tests`, `blocked`, `future`
- Alan: `data`, `analytics`, `dashboard`, `api`, `project-management`
- Mevcut eski `type:*`, `area:*` ve `priority:*` etiketleri geriye dönük
  kayıtlar için korunabilir.

## Veri Yönetimi Notu

Olist CSV dosyaları repo'ya commitlenmez. Yüklenen arşiv yalnızca local schema doğrulama, data-quality kontrolü ve dokümantasyon tutarlılığı için referans olarak kullanılır.
