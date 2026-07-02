# Optional GCP / BI Handoff

This project is local-first. GCP is an optional presentation and analytics
handoff path after the local SQLite workflow has already produced validated SQL
marts.

## Scope Boundary

Use this path for:

- loading exported mart CSV files into BigQuery for SQL exploration
- connecting Looker Studio to BigQuery tables or views
- demonstrating cloud-aware analytics delivery without changing the local app

Do not treat this as:

- a production deployment
- a measured business-impact environment
- a required runtime for Streamlit, FastAPI, notebooks, or tests

Out of scope for V1: GKE, Cloud Composer, Cloud SQL, Vertex AI training,
service-account key files in the repository, scheduled cloud pipelines, and
always-on dashboards.

## Local Prerequisite

Run the full local workflow first:

```bash
python -m src.ml.ingest
python scripts/validate_olist_schema.py --target all
make bi-export
```

`make bi-export` writes CSV files and `manifest.json` under
`data/exports/bi/`. The `data/` directory is Git-ignored, so these outputs stay
local.

## Cost Guardrails

- Use a separate demo project if you test GCP.
- Set a budget alert before loading or querying data.
- Avoid scheduled refreshes until there is a real review need.
- Delete demo BigQuery datasets and Cloud Storage buckets when finished.
- Do not commit service-account JSON, `.env`, exported CSV files, or local
  manifests.

Looker Studio's BigQuery connector can incur BigQuery usage costs, so this path
should remain optional.

## BigQuery Load Path

The generated BI files can be loaded as BigQuery tables with the `bq` CLI. This
keeps the repository free of cloud SDK dependencies.

```bash
export GCP_PROJECT="your-gcp-project"
export BQ_DATASET="olist_intelligence_demo"

bq --project_id="${GCP_PROJECT}" mk --dataset "${GCP_PROJECT}:${BQ_DATASET}"

for file in data/exports/bi/*.csv; do
  table="$(basename "${file}" .csv)"
  bq --project_id="${GCP_PROJECT}" load \
    --autodetect \
    --source_format=CSV \
    --skip_leading_rows=1 \
    "${GCP_PROJECT}:${BQ_DATASET}.${table}" \
    "${file}"
done
```

For repeatable portfolio demos, prefer loading the exported marts rather than
the raw Kaggle tables. The marts already encode grain rules such as
order-level aggregation before seller/category summaries.

## Looker Studio Path

After loading the tables:

1. Open Looker Studio.
2. Create a report.
3. Add a BigQuery data source.
4. Choose the demo project and `olist_intelligence_demo` dataset.
5. Start with these tables:
   - `executive_order_summary`
   - `seller_risk_scorecard`
   - `category_performance_summary`
   - `location_service_level_summary`
   - `customer_cohort_retention`

Recommended report pages:

- Executive status: orders, product revenue, payment mix, review score.
- Seller operations: seller SLA plus seller risk scorecard.
- Category and lane quality: category performance and state-lane service
  levels.
- Retention: cohort retention heatmap or filtered table.

## Claim Boundary

Cloud export proves that the marts can be handed to BI tooling. It does not
prove production reliability, automated orchestration, model impact, or
business uplift.

Keep public wording aligned with:

- source baseline: what the historical Olist data shows
- offline benchmark: how a model performed on a holdout split
- scenario target: a future operational goal
- BI export: a local-to-cloud handoff option

## References

- BigQuery CSV load documentation:
  https://cloud.google.com/bigquery/docs/loading-data-cloud-storage-csv
- BigQuery `bq` CLI quickstart:
  https://cloud.google.com/bigquery/docs/bq-command-line-tool
- Looker Studio BigQuery connector:
  https://support.google.com/looker-studio/answer/6370296
