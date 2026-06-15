# Olist Intelligence Architecture

## System Overview

Olist Intelligence is a local portfolio analytics application built around the
public Olist Kaggle dataset. It combines local ingestion, schema and quality
checks, reusable SQL views, repository/service functions, a Streamlit
dashboard, and FastAPI model endpoints.

It is not presented as a production data platform. Raw data and generated
artifacts remain local.

## Data Flow

1. The user downloads the 9 expected Olist CSV files from Kaggle.
2. `src/ml/ingest.py` loads raw files into local SQLite tables or a configured
   `DATABASE_URL`.
3. `src/data_contract.py` and `scripts/validate_olist_schema.py` validate raw
   schemas, database schemas, and data-quality rules.
4. `sql/views/` creates reusable analytics views for executive, delivery,
   payment, cohort, seller, and segment reporting.
5. `src/database/` repository functions query raw tables and SQL views.
6. `src/services/` packages repository results for consumers.
7. `src/views/` and `src/dashboard.py` render dashboard views; `src/app.py`
   exposes FastAPI endpoints.
8. Notebook workflows may create local `logistics_predictions` and
   `customer_segments` tables used by selected dashboard pages.

Editable diagram source:
[`architecture.excalidraw`](architecture.excalidraw)

The existing rendered overview remains available at
[`../../docs/architecture.md`](../../docs/architecture.md).

## Module Responsibilities

| Area | Responsibility |
| --- | --- |
| `src/data_contract.py` | Canonical raw-file, table, and quality contract |
| `src/ml/ingest.py` | Local CSV-to-database ingestion |
| `scripts/validate_olist_schema.py` | CLI validation entry point |
| `sql/views/` | Reusable analytics marts/views |
| `src/database/db_client.py` | Database engine creation |
| `src/database/repository.py` | Backward-compatible repository facade and remaining legacy functions |
| `src/database/*_repository.py` | Focused repository modules introduced through small refactors |
| `src/database/*_schema.py`, constants, helpers | Stable return shapes, names, limits, and fallback helpers |
| `src/services/` | Consumer-facing analytics and API service logic |
| `src/views/`, `src/dashboard.py` | Streamlit dashboard presentation |
| `src/app.py` | FastAPI routes and health/config behavior |

## Repository Layer Design

The repository layer is being cleaned in small PRs. Existing imports and return
shapes must remain compatible while functions gradually move into focused
modules.

Current extracted modules include `action_repository.py` and
`ranking_repository.py`. Shared helper modules define query limits, empty
DataFrame schemas, metric/table names, dates, and fallback values.

`repository.py` remains the compatibility facade until callers are migrated and
covered by regression tests. A full-file rewrite is intentionally avoided.

## Current Analytics

- Revenue and order KPIs
- Delivery/logistics KPIs and prototype predictions
- Review and customer-quality metrics
- Payment mix
- Cohort retention
- Product/category rankings and seller SLA watchlist
- Generated customer segment summaries

## Future Analytics

The following are planned, not implemented as completed features:

- Portuguese review-text issue analysis
- Customer/seller/geolocation service-level analysis
- Seller and customer segmentation improvements
- Expanded product/category performance analysis

## Current Limitations

- Local raw data and generated tables are required for complete dashboard
  behavior.
- Repository responsibilities are not fully split by domain.
- Some broad exception fallbacks remain and should be improved in small PRs.
- Delivery claims require strict temporal validation; repeat-purchase modeling
  is skipped when the class-balance gate fails.
- SQLite-oriented date functions in some views require review before a database
  portability claim.
