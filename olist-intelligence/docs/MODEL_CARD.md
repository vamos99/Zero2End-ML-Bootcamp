# Model Card

This project contains prototype models for a bootcamp portfolio project. The models support dashboard storytelling and local experimentation; they are not production scoring systems.

## Delivery time model

| Field | Description |
| --- | --- |
| Task | Predict delivery duration in days. |
| Algorithm | CatBoost regressor. |
| Main features | Freight value, price, product weight, description length, distance proxy, same-state flag, seller rating proxy. |
| Reported metric | Notebook output reports roughly 7.6 days RMSE. |
| Intended use | Local dashboard and methodology demonstration. |
| Not intended for | SLA automation, customer-facing delivery guarantees, or operational dispatch decisions. |

### Known limitations

- The model depends on derived features created in notebooks or local preprocessing.
- Reported performance should be regenerated from the raw Olist data before being cited as current.
- Some features are proxies and may not transfer to live e-commerce operations.
- Error should be reviewed by order state, seller region, and product category before using the output for decisions.

## Churn model

| Field | Description |
| --- | --- |
| Task | Classify customer churn or churn risk using RFM-style inputs. |
| Algorithm | CatBoost classifier. |
| Main features | Recency, frequency, monetary value. |
| Churn proxy | No order for 90 days is treated as churn/risk in the project narrative. |
| Intended use | Dashboard segmentation and retention-risk demonstration. |
| Not intended for | Automated campaign targeting without validation. |

### Known limitations

- The target is a proxy, not a business-confirmed churn label.
- Time-based train/test validation should be preferred over random split before presenting the model as predictive.
- Class imbalance and leakage risk must be checked when regenerating results.
- Results should be interpreted alongside cohort and retention SQL metrics, not alone.

## Recommender

| Field | Description |
| --- | --- |
| Task | Recommend products or categories for a customer. |
| Algorithm | SVD-style collaborative filtering prototype with fallback logic. |
| Intended use | Local demo of recommendation flow. |
| Not intended for | Production ranking or personalization. |

### Known limitations

- Cold-start behavior falls back to popularity-based recommendations.
- Offline evaluation coverage is limited in the current project state.
- Recommendation quality should be checked with coverage, diversity, and hit-rate style metrics before further claims.

## Validation checklist before presenting results

- Re-run ingestion from the raw Olist CSV files.
- Run CSV, DB, and quality validation scripts.
- Re-run notebooks or training scripts that generate model artifacts.
- Record the exact metric values and split strategy used.
- Confirm dashboard screenshots come from the same validated local database.
