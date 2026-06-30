# Analytics SQL Layer

This folder documents the analytical views used to explain the project from a
data engineering and analytics perspective. The app can run without applying
these files, but they make the data model easier to inspect in SQLite or
Postgres-like environments.

## Views

- `executive_order_summary.sql`: daily order, customer, and revenue metrics.
- `delivery_quality.sql`: delivery lateness and review-score quality signals.
- `seller_performance.sql`: seller revenue, review, and delivery reliability.
- `payment_mix_summary.sql`: payment type, installment and payment-value mix.
- `review_delivery_drivers.sql`: review-score buckets versus delivery quality.
- `seller_sla_summary.sql`: seller-level SLA, revenue, item and review metrics.
- `category_performance_summary.sql`: category revenue, review, and delivery
  quality metrics.
- `customer_cohort_retention.sql`: monthly cohort retention using
  `customer_unique_id`.
- `customer_segment_summary.sql`: RFM segment summary after the segmentation
  notebook creates `customer_segments`.

See [`METRICS.md`](METRICS.md) for the metric dictionary and reconciliation
coverage.

## Local Usage

After the Kaggle Olist data has been ingested into `olist.db`, apply all views:

```bash
cd olist-intelligence
python scripts/apply_sql_views.py --replace
```

If you only want to apply missing views without replacing existing definitions,
drop `--replace`.

Before applying views or running model notebooks, validate that the local raw
CSV files or the ingested database still match the Kaggle Olist source contract:

```bash
python scripts/validate_olist_schema.py --target csv
python scripts/validate_olist_schema.py --target db
python scripts/validate_olist_schema.py --target quality
```

`--target quality` requires an ingested database. It checks stable rules such as
empty source tables, duplicate business keys, orphan joins, accepted order and
payment values, invalid review scores, negative amounts, and impossible delivery
dates. If `olist.db` is missing, failing fast is expected.

For manual SQLite inspection:

```bash
sqlite3 olist.db < sql/views/executive_order_summary.sql
sqlite3 olist.db "SELECT * FROM executive_order_summary LIMIT 10;"
```

## Scope

These views are intentionally lightweight. They are not a replacement for a
production warehouse, but they show the same modeling habit: separate raw
source tables from reusable analytical outputs, and keep quality checks close to
the source contract.
