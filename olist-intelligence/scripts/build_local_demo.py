"""Build a deterministic local dashboard dataset from an ingested Olist database."""

from __future__ import annotations

import argparse
import os
import sys
import warnings
from pathlib import Path

if not os.environ.get("LOKY_MAX_CPU_COUNT"):
    os.environ["LOKY_MAX_CPU_COUNT"] = "1"
warnings.filterwarnings(
    "ignore",
    message="Could not find the number of physical cores",
    module="joblib.externals.loky.backend.context",
)

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler
from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from scripts.apply_sql_views import apply_sql_views  # noqa: E402
from src.config import DATABASE_URL  # noqa: E402
from src.data_contract import validate_database_quality, validate_generated_outputs  # noqa: E402


SEGMENT_NAMES = ["⚠️ At Risk", "🌱 Developing", "🏆 Loyal", "💎 Champions"]


def build_logistics_baseline(engine) -> int:
    """Create an honest SLA-estimate baseline for dashboard workflow QA."""
    query = text("""
    SELECT
        o.order_id,
        o.customer_id,
        JULIANDAY(o.order_estimated_delivery_date) - JULIANDAY(o.order_purchase_timestamp)
            AS predicted_delivery_days,
        JULIANDAY(o.order_delivered_customer_date) - JULIANDAY(o.order_purchase_timestamp)
            AS delivery_days,
        'olist_estimated_date_baseline' AS prediction_source
    FROM orders o
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp IS NOT NULL
      AND o.order_estimated_delivery_date IS NOT NULL
      AND o.order_delivered_customer_date IS NOT NULL
    """)
    frame = pd.read_sql(query, engine).dropna()
    frame = frame[
        (frame["predicted_delivery_days"] > 0)
        & (frame["delivery_days"] > 0)
    ].drop_duplicates("order_id")
    frame.to_sql("logistics_predictions", engine, if_exists="replace", index=False)
    return len(frame)


def build_customer_segments(engine) -> tuple[int, dict[str, float]]:
    """Create the same deterministic relative RFM profiles used by notebook 4."""
    query = text("""
    WITH params AS (
        SELECT MAX(order_purchase_timestamp) AS dataset_end
        FROM orders
        WHERE order_status = 'delivered'
    ), customer_stats AS (
        SELECT
            c.customer_unique_id,
            MAX(o.order_purchase_timestamp) AS last_purchase,
            COUNT(DISTINCT o.order_id) AS frequency,
            SUM(oi.price + oi.freight_value) AS monetary
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        JOIN order_items oi ON o.order_id = oi.order_id
        WHERE o.order_status = 'delivered'
        GROUP BY c.customer_unique_id
    )
    SELECT
        customer_unique_id,
        CAST(JULIANDAY(p.dataset_end) - JULIANDAY(last_purchase) AS INTEGER) AS recency,
        frequency,
        monetary
    FROM customer_stats
    CROSS JOIN params p
    WHERE monetary > 0
    """)
    frame = pd.read_sql(query, engine).dropna()
    model_features = frame[["recency", "frequency", "monetary"]].copy()
    for column in model_features:
        lower, upper = model_features[column].quantile([0.01, 0.99])
        model_features[column] = model_features[column].clip(lower, upper)

    scaled = StandardScaler().fit_transform(model_features)
    frame["cluster"] = KMeans(n_clusters=4, random_state=42, n_init=10).fit_predict(scaled)
    alternate_labels = KMeans(n_clusters=4, random_state=7, n_init=10).fit_predict(scaled)
    sample_size = min(10_000, len(frame))
    sample_indices = frame.sample(n=sample_size, random_state=42).index
    stability_metrics = {
        "segment_stability_ari": float(adjusted_rand_score(frame["cluster"], alternate_labels)),
        "segment_silhouette_sample": float(
            silhouette_score(scaled[sample_indices], frame.loc[sample_indices, "cluster"])
        ),
    }
    summary = frame.groupby("cluster").agg(
        recency=("recency", "mean"),
        frequency=("frequency", "mean"),
        monetary=("monetary", "mean"),
    )
    profile_score = (
        -summary["recency"].rank(pct=True)
        + summary["frequency"].rank(pct=True)
        + summary["monetary"].rank(pct=True)
    )
    segment_map = dict(zip(profile_score.sort_values().index.tolist(), SEGMENT_NAMES))
    frame["segment"] = frame["cluster"].map(segment_map)
    frame = frame.rename(
        columns={
            "recency": "Recency",
            "frequency": "Frequency",
            "monetary": "Monetary",
            "cluster": "Cluster",
            "segment": "Segment",
        }
    )
    frame.to_sql("customer_segments", engine, if_exists="replace", index=False)
    return len(frame), stability_metrics


def build_local_demo(database_url: str) -> dict[str, int]:
    quality_issues = validate_database_quality(database_url)
    if quality_issues:
        details = "; ".join(f"{issue.name}:{issue.issue}" for issue in quality_issues[:5])
        raise RuntimeError(f"Raw database quality checks failed: {details}")

    engine = create_engine(database_url)
    logistics_rows = build_logistics_baseline(engine)
    segment_rows, stability_metrics = build_customer_segments(engine)
    applied, skipped = apply_sql_views(
        database_url,
        PROJECT_ROOT / "sql" / "views",
        strict=True,
        replace=True,
    )
    if skipped:
        raise RuntimeError(f"SQL views skipped unexpectedly: {skipped}")

    generated_issues = validate_generated_outputs(database_url)
    if generated_issues:
        details = "; ".join(f"{issue.name}:{issue.issue}" for issue in generated_issues[:5])
        raise RuntimeError(f"Generated output checks failed: {details}")

    metadata = pd.DataFrame(
        [
            {"metric_name": name, "metric_value": value, "details": "deterministic local demo build"}
            for name, value in stability_metrics.items()
        ]
    )
    metadata.to_sql("generated_output_metadata", engine, if_exists="replace", index=False)

    return {
        "logistics_predictions": logistics_rows,
        "customer_segments": segment_rows,
        "sql_views": len(applied),
        **stability_metrics,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic local Olist dashboard outputs.")
    parser.add_argument("--database-url", default=DATABASE_URL)
    args = parser.parse_args()

    result = build_local_demo(args.database_url)
    print(
        "[local-demo] ok: "
        f"{result['logistics_predictions']} logistics rows, "
        f"{result['customer_segments']} segment rows, "
        f"{result['sql_views']} SQL views, "
        f"segment ARI {result['segment_stability_ari']:.3f}, "
        f"silhouette {result['segment_silhouette_sample']:.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
