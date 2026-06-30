# Measured Results

Bu sayfa, local Olist veritabanı ve repo içindeki çalıştırılabilir scriptlerle
üretilen sayısal sonuçları özetler. Değerler production etkisi veya gerçek
kampanya uplift'i değildir; bootcamp/portfolio prototipinin ölçülen teknik ve
analitik çıktılarıdır.

Son ölçüm: 2026-06-30, local SQLite snapshot.

## Outcome vs. Business Impact

Bu projede canlı operasyon veya A/B test yoktur. Bu yüzden "teslim süresi şu
kadar iyileşti", "churn şu kadar azaldı" veya "satış şu kadar arttı" gibi
iş etkisi iddiaları ölçülmüş sonuç değildir. Ölçülen sonuçlar aşağıdaki
model/analytics benchmark'larıdır.

`scripts/evaluate_olist_results.py --pretty` çıktısındaki `evidence_rows`
alanı bu ayrımı makine-okunur şekilde de üretir. Böylece README, notebook ve
dashboard metinleri aynı sınırı kullanır: source baseline mevcut durumu,
offline benchmark model tahmin kalitesini, scenario ise gelecek deney hedefini
anlatır.

Aynı script içindeki `outcome_scorecard` alanı, okuyucuya doğrudan
"önce neydi, şimdi ne ölçüldü, ne gerçekten değişti?" sorusunun cevabını verir.
Bu yüzden teslimat veya churn için operasyonel iyileşme iddiası ancak
`measured_change` alanında açıkça kanıt varsa yazılmalıdır.
Dashboard ana sayfasındaki outcome scorecard da aynı ayrımı hafif servis
verisiyle gösterir; sayfa açılışında model benchmark'ı yeniden eğitmez.

| Alan | Ölçülen sonuç | Ölçülmeyen iş etkisi |
| --- | --- | --- |
| Source delivery baseline | Geç teslimat oranı %6.77; geç kalanlarda ortalama gecikme 10.62 gün | Model sonrası teslimat azalması ölçülmedi |
| Delivery prediction | Mean baseline'a göre RMSE %8.8, MAE %15.1 daha düşük; Olist estimated-date duration baseline'a göre RMSE %28.0, MAE %48.2 daha düşük | Gerçek teslim süresi azalması ölçülmedi |
| Source repeat-purchase baseline | Repeat-customer oranı %3.00; one-time customer oranı %97.00 | Churn/retention iyileşmesi ölçülmedi |
| Repeat-purchase risk | Sınıf dağılımı %99.40 risk etiketi; model gate failed | Churn azalması veya kampanya uplift'i ölçülmedi |
| Recommender | Hit rate @10 = %3.51; random catalog baseline'a göre yaklaşık 116x | Satış veya sepet artışı ölçülmedi |
| Executive analytics marts | Credit card payment share %78.34; month-1 retention %5.20; 2,970 seller SLA rows; 93,358 segmented customers | Operasyonel müdahale sonrası değişim ölçülmedi |
| Segmentation | 93,358 müşteri segmentlendi; ARI 1.000, silhouette 0.479 | Segment bazlı kampanya dönüşümü ölçülmedi |
| Cohort/payment/seller analytics | SQL martlarla retention, payment mix ve seller SLA ölçüldü | Operasyonel müdahale sonrası değişim ölçülmedi |

## Source Coverage

| Alan | Sonuç |
| --- | ---: |
| Orders | 99,441 |
| Delivered orders | 96,478 |
| Unique customer records | 99,441 |
| Unique long-term customers | 96,096 |
| Order item rows | 112,650 |
| Reviews | 99,224 |
| Product revenue | 13,591,643.70 BRL |
| Freight value | 2,251,909.54 BRL |
| Average product order value | 136.68 BRL |
| Average review score | 4.09 / 5 |

## Delivery And Logistics

| Metrik | Sonuç | Yorum |
| --- | ---: | --- |
| Delivered orders with delivery/estimate dates | 96,470 | Delivery KPI denominator |
| Late delivered orders | 6,534 | Delivered after estimated date |
| Late delivery rate | 6.77% | SLA risk baseline |
| Local logistics prediction rows | 96,470 | Generated dashboard output |
| Baseline on-time rate | 91.89% | Actual delivery days <= Olist estimated-date baseline |
| Long-delivery baseline rows | 92,525 | Estimated delivery duration > 10 days |
| Long-delivery baseline share | 95.91% | Broad operational backlog signal, not a defect rate |

Interpretation: the source-data starting point is a 6.77% late-delivery rate.
Late orders arrive 10.62 days late on average when lateness is measured by
calendar date. The model section below does not prove this rate fell; it only
shows whether a prediction model beats a naive prediction baseline.

### Delivery Model Holdout

The CatBoost delivery prototype was evaluated in-memory with a later-order
temporal holdout. No model file was overwritten during this measurement.

| Metrik | Sonuç |
| --- | ---: |
| Rows used | 48,859 |
| Features | 10 |
| Train rows | 39,087 |
| Test rows | 9,772 |
| RMSE | 10.55 days |
| MAE | 6.52 days |
| R2 | 0.076 |
| Test actual mean | 15.90 days |
| Test prediction mean | 11.96 days |
| Source estimated-date mean | 26.01 days |
| Train-mean baseline RMSE | 11.57 days |
| Train-mean baseline MAE | 7.68 days |
| Source estimated-date RMSE | 14.66 days |
| Source estimated-date MAE | 12.59 days |
| RMSE improvement vs. train-mean baseline | 8.8% |
| MAE improvement vs. train-mean baseline | 15.1% |
| RMSE improvement vs. source estimated-date baseline | 28.0% |
| MAE improvement vs. source estimated-date baseline | 48.2% |
| MAE as share of mean delivery time | 41.0% |
| RMSE as share of mean delivery time | 66.3% |
| Mean prediction gap | -3.94 days / -24.8% |
| Source estimate gap | +10.11 days / +63.6% |
| Variance explained by model | 7.6% |

Interpretation: the average absolute error is 6.52 days on a test set where
the average delivery time is 15.90 days. In plain terms, a typical prediction is
off by about 41% of the average delivery duration, and the model explains only
7.6% of the variation in delivery days.

Against a simple "predict the train-set average delivery time" baseline, the
model improves RMSE by 8.8% and MAE by 15.1%. That is a measurable prediction
improvement, not a measured delivery-time improvement. Against Olist's source
estimated-date duration baseline on the same holdout, the model improves RMSE
by 28.0% and MAE by 48.2%. The safer portfolio framing is "delivery-risk
prototype that improves offline prediction baselines but still needs better
calibration", not "delivery time improved by X%".

## Repeat-Purchase / Churn Candidate

The current repeat-purchase target is a modeling suitability check, not a
served churn model. The local snapshot is too imbalanced for decision-ready
classification.

| Metrik | Sonuç |
| --- | ---: |
| Sample rows | 50,000 |
| Returned within label window (`0`) | 298 |
| No repeat purchase in label window (`1`) | 49,702 |
| Positive risk share | 99.40% |
| Model evaluation gate | Failed |

Interpretation: this should be documented as a repeat-purchase risk analysis
gate. Cohort retention is the better source-backed customer behavior view until
a stronger time-window definition is built.

The source-data repeat-purchase baseline is also low: 2,801 of 93,358 unique
customers have more than one delivered order, or 3.00%. This is a business
opportunity baseline, not a measured retention improvement.

## Planning Scenarios, Not Measured Impact

These rows translate the source baselines into concrete planning numbers. They
are not results that already happened.

| Scenario | Baseline | Projected after assumption | Delta |
| --- | ---: | ---: | ---: |
| Prevent 10% of late deliveries | 6.77% late rate | 6.10% late rate | -0.68 pp; 653 late orders; 6,939 late-days |
| Prevent 20% of late deliveries | 6.77% late rate | 5.42% late rate | -1.35 pp; 1,307 late orders; 13,878 late-days |
| Increase repeat customers by +0.5 pp | 3.00% repeat rate | 3.50% repeat rate | +467 repeat customers |
| Increase repeat customers by +1.0 pp | 3.00% repeat rate | 4.00% repeat rate | +934 repeat customers |
| Increase repeat customers by +2.0 pp | 3.00% repeat rate | 5.00% repeat rate | +1,867 repeat customers |

Use these as experiment targets or dashboard scenario values. They become
"impact" only after a controlled experiment, holdout campaign, or
post-intervention operations log confirms the change.

## Recommender Prototype

| Metrik | Sonuç |
| --- | ---: |
| Interaction rows | 101,987 |
| Users | 95,420 |
| Products | 32,951 |
| Leave-one-out users evaluated | 3,987 |
| Hit rate @10 | 3.51% |
| Catalog coverage @10 | 0.29% |
| Random catalog hit rate @10 | 0.03% |
| Lift vs. random catalog baseline | 115.7x |

Interpretation: known-user personalization works as an API/demo path, while
offline ranking quality is still early-stage. The model is far above a random
catalog baseline, but the absolute hit rate is still low and no sales uplift was
measured. Unknown customers correctly fall back to popular category
recommendations and are labeled as fallback output.

## Segmentation And Customer Analytics

`scripts/build_local_demo.py` generated 93,358 customer segment rows.

| Segment | Customers | Avg. recency | Avg. frequency | Avg. monetary |
| --- | ---: | ---: | ---: | ---: |
| Developing | 49,290 | 127.0 | 1.00 | 123.38 BRL |
| At Risk | 36,726 | 386.5 | 1.00 | 124.10 BRL |
| Loyal | 4,541 | 231.5 | 1.00 | 862.47 BRL |
| Champions | 2,801 | 219.3 | 2.11 | 308.53 BRL |

Technical diagnostics:

- Segment stability ARI: 1.000
- Sample silhouette score: 0.479

## Executive Analytics Signals

| Alan | Sonuç |
| --- | ---: |
| SQL views applied | 8 |
| Month-1 average cohort retention | 5.20% |
| Month-2 average cohort retention | 0.33% |
| Seller SLA rows | 2,970 sellers |
| Average seller late-delivery rate | 6.91% |
| Max seller late-delivery rate | 100.00% |
| Generated logistics prediction rows | 96,470 |
| Generated customer segment rows | 93,358 |
| Largest segment | Developing, 49,290 customers |

Payment value by method:

| Payment type | Payment value | Orders |
| --- | ---: | ---: |
| Credit card | 12,542,084.19 BRL | 76,505 |
| Boleto | 2,869,361.27 BRL | 19,784 |
| Voucher | 379,436.87 BRL | 3,866 |
| Debit card | 217,989.79 BRL | 1,528 |

## Reproducibility Commands

```bash
python scripts/build_local_demo.py
python scripts/validate_olist_schema.py --target all
python scripts/evaluate_olist_results.py --pretty
python -m pytest -q
```

`scripts/evaluate_olist_results.py` recomputes the delivery baseline
comparison, source business baselines, planning scenarios, repeat-purchase gate,
recommender offline benchmark, SQL mart operating signals, and generated-output
coverage against the current local `olist.db` without writing model artifacts.
