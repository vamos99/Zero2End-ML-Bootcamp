# Proje Yönetimi

Bu dosya, **Olist Intelligence Suite** çalışmasının GitHub Projects, issue ve PR
akışıyla nasıl takip edildiğini açıklar. Ana takip yeri GitHub Project board'dur;
bu dosya ise board'un alanlarını, iş kurallarını ve güncel backlog özetini repo
içinde kalıcı hale getirir.

## GitHub Project

- Board: [Olist Analytics Board](https://github.com/users/vamos99/projects/3)
- Durum: public
- Amaç: Olist projesindeki hata, dokümantasyon, validasyon ve küçük refactor
işlerini küçük, izlenebilir ve PR bazlı parçalarla yönetmek.

## Board Alanları

| Alan | Değerler | Kullanım |
| --- | --- | --- |
| Status | Backlog, Ready, In Progress, Review, Done | İşin gerçek akış durumunu gösterir. |
| Priority | P0, P1, P2 | P0 çalışmayı bozan kritik hata; P1 yakın vadeli düzeltme; P2 iyileştirme/fikir. |
| Area | analytics, dashboard, data-pipeline, ml, docs, ci, api | İşin ana teknik alanı. |
| Size | S, M, L | S tek dosya/küçük test; M birkaç dosya; L ayrı tasarım gerektiren iş. |
| Sprint | Stabilization, Validation, Enhancement | Önce mevcut işleri sağlamlaştırma, sonra doğrulama, en son yeni geliştirme. |

## Label Standardı

Board alanlarının issue/PR üzerinde de görünmesi için label isimleri aynı mantıkla
kullanılır.

| Label grubu | Örnekler |
| --- | --- |
| Type | `type: bug`, `type: docs`, `type: task`, `type: refactor`, `type: experiment` |
| Area | `area: dashboard`, `area: api`, `area: ml`, `area: data-pipeline`, `area: analytics`, `area: docs`, `area: ci` |
| Priority | `priority: P0`, `priority: P1`, `priority: P2` |

## Çalışma Akışı

1. Yeni iş önce issue olarak açılır ve board'da **Backlog** veya **Ready** durumuna
   alınır.
2. Kod veya doküman değişikliği ayrı branch üzerinde yapılır. Branch adı issue
   numarasını içermelidir.
3. Her branch tek amaçlı tutulur. Bir PR içinde çok sayıda alakasız düzeltme
   yapılmaz.
4. PR açılınca issue board'da **Review** durumuna taşınır.
5. PR açıklaması kısa olur: ne değişti, nasıl doğrulanır, hangi issue kapanır.
6. PR merge edilince ilgili issue **Done** durumuna taşınır.
7. Yeni özelliklere geçmeden önce açık bug, docs ve validasyon işleri kapatılır.

## Issue Hazırlık Kriteri

- Kullanıcıya, dashboard'a veya veri doğruluğuna etkisi bir cümleyle yazılmış
  olmalı.
- Kullanılacak veri kaynağı, tablo veya endpoint belirtilmeli.
- Kabul kriterinde en az bir doğrulama adımı olmalı.
- Secret, özel veri, Kaggle dosyası veya deployment varsayımı varsa açıkça
  yazılmalı.
- İş algoritma denemesi ise mevcut modeli değiştirmeden önce hipotez ve ölçüm
  metriği yazılmalı.

## Done Kriteri

- Değişiklik feature branch üzerinde commitlenmiş olmalı.
- İlgili test, validation veya doküman kontrolü tanımlanmış olmalı.
- SQL/dashboard/API davranışı değiştiyse README, metric docs veya runbook
  güncellenmiş olmalı.
- PR açıklaması kısa maddelerle ne değiştiğini ve doğrulama durumunu anlatmalı.
- Büyük refactor yapılmadıysa PR kapsamı küçük kalmalı; büyük refactor ayrı issue
  olarak açılmalı.

## Güncel İş Durumu

| Durum | Öncelik | Alan | İş | Kayıt |
| --- | --- | --- | --- | --- |
| Review | P1 | dashboard/api | Recommendation client payload API şemasıyla hizalanacak | #18 / #19 |
| In Progress | P1 | docs | Project board ve aktif backlog dokümanı gerçek kullanım akışına göre düzenlenecek | #20 |
| Ready | P1 | data-pipeline | Yüklenen Olist CSV paketi schema contract ile doğrulanacak | Açılacak issue |
| Ready | P1 | api | API endpoint güvenlik kapsamı gözden geçirilecek | Açılacak issue |
| Ready | P2 | ml | Delivery/churn model card hazırlanacak | Açılacak issue |
| Backlog | P2 | docs | Dashboard ekran görüntüleri yerel veriyle yeniden üretilecek | Açılacak issue |

## Tamamlanan İşler

| Alan | İş | Kanıt |
| --- | --- | --- |
| analytics | Executive KPI metric dictionary | `olist-intelligence/sql/METRICS.md` |
| data-pipeline | Kaggle source schema contract | `olist-intelligence/src/data_contract.py` |
| data-pipeline | DB kalite kontrolleri | `olist-intelligence/tests/test_data_contract.py` |
| analytics | Payment, review-delivery ve seller SLA marts | `olist-intelligence/sql/views/`, `tests/test_sql_views.py` |
| analytics | Cohort/retention mart | `olist-intelligence/sql/views/customer_cohort_retention.sql`, `tests/test_sql_views.py` |
| dashboard | Executive dashboard SQL mart eşlemesi | `olist-intelligence/src/views/home_view.py`, `olist-intelligence/README.md` |
| ci | Küçük SQLite fixture testleri | `olist-intelligence/tests/` |

## Yeni Geliştirme Öncesi Kapanması Gerekenler

1. Dashboard ve API arasındaki payload/endpoint sözleşmeleri netleştirilmeli.
2. Kaggle/Olist CSV paketi data contract ile doğrulanmalı.
3. README'deki kurulum, veri hazırlama ve validasyon komutları mevcut kodla
   uyumlu hale getirilmeli.
4. Model sonuçları için sınırlılık ve doğrulama notları ayrı model card olarak
   yazılmalı.
5. Dashboard ekran görüntüleri yalnızca doğrulanmış lokal veriyle yenilenmeli.

## Ertelenen Fikirler ve Algoritma Denemeleri

Bu bölüm yeni özellik backlog'u değildir. Mevcut proje sağlamlaştırıldıktan sonra
hipotez bazlı deney olarak ele alınabilir.

| Fikir | Neden ertelendi | Gerekli ölçüm |
| --- | --- | --- |
| Firefly / meta-sezgisel optimizasyon denemesi | Şu anki problemde önce mevcut ML ve dashboard sözleşmeleri stabilize edilmeli. | Mevcut baseline'a göre RMSE, latency veya karar kalitesi etkisi. |
| Alternatif recommender yaklaşımı | Önce mevcut `/recommend` API sözleşmesi ve fallback akışı düzeltilmeli. | Hit-rate proxy, kategori çeşitliliği, cold-start davranışı. |
| Daha gelişmiş churn temporal split | Mevcut churn prototipi önce model card ve leakage notuyla açıklanmalı. | Zaman bazlı train/test skoru ve leakage kontrolü. |

## PR Yazım Formatı

Her PR açıklaması kısa tutulur:

```markdown
## Summary
- ...
- ...

## Validation
- ...

Closes #issue_no
```

## Veri Yönetimi Notu

Raw Olist CSV dosyaları repo'ya commitlenmez. Yüklenen `archive.zip` yalnızca local
schema doğrulama, data-quality kontrolü ve dokümantasyon tutarlılığı için referans
olarak kullanılır.
