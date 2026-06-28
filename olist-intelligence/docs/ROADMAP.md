# Olist Intelligence Roadmap

The GitHub
[Olist Analytics Board](https://github.com/users/vamos99/projects/3) is the
canonical status tracker. This file provides a stable phase summary and does
not replace issues or project cards.

## Completed Foundation

- Kaggle source schema contract for 9 CSV files and 52 required columns
- Local dataset and `olist.db` Git/Docker guardrails
- CSV, database-schema, and data-quality validation commands
- Reusable SQL views for executive, delivery, payment, cohort, seller, and
  segment reporting
- Dashboard operating signals for payment mix, cohort retention, and seller SLA
- GitHub Actions syntax and test checks
- Shared repository contracts and two real helper-integration batches
- Complete ranking repository behavior with stable fallback contracts
- Backward-compatible ranking and action domain splits
- API key/config and SQL-view reconciliation tests
- Architecture overview and local onboarding instructions
- Deterministic local demo build and generated-output contracts
- Dashboard empty-state/readiness semantics and relative segment labels
- Delivery seller-rating leakage guardrail and model cards
- Logistics and customer repository domain splits with compatibility wrappers
- Recommender leave-one-out evaluation and unseen-product inference guardrail
- Source baseline and scenario target cards on the executive dashboard

## Remaining Cleanup Before New Analytics

- Split remaining executive/revenue/review domains behind compatibility wrappers.
- Add focused ingest, registry, and Docker startup tests.
- Keep project board, docs, screenshots, and actual code status aligned.

## Next Analytics Phases

These items are future work and must remain Backlog or Ready until code,
tests, and documentation exist.

### Review Text Analysis

Use Portuguese review title/message fields for a small, explainable issue-bucket
experiment. Document missing-text coverage, language handling, and limitations.

### Geolocation And Location Analysis

Aggregate ZIP-prefix geolocation before joining customer and seller locations.
Focus on delivery/service-level patterns rather than decorative maps.

### Seller And Customer Segmentation

Improve seller-performance groupings and review existing customer RFM/segment
logic. Preserve the distinction between `customer_id` and
`customer_unique_id`.

### Product And Category Performance

Expand category and seller ranking functions with clear grains, bounded limits,
and reusable repository contracts.

### Retention And Churn Methodology

Keep cohort retention as the source-backed behavior view. Rebuild predictive
churn only with a time-based feature/label design that avoids target proxies.

## Guardrails

- Do not commit raw data, local databases, model artifacts, or credentials.
- Do not mark future analytics as completed before implementation and tests.
- Do not combine repository rewrites with analytics feature development.
- Keep PRs reviewable and retain compatibility wrappers during module moves.
