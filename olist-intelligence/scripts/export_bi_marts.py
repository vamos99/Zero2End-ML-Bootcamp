"""Export dashboard SQL marts as local BI-ready CSV files."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from scripts.apply_sql_views import apply_sql_views  # noqa: E402
from src.config import DATABASE_URL  # noqa: E402


@dataclass(frozen=True)
class MartExport:
    name: str
    source_name: str
    file_name: str
    description: str
    order_by: str | None = None


BI_MARTS = (
    MartExport(
        name="executive_order_summary",
        source_name="executive_order_summary",
        file_name="executive_order_summary.csv",
        description="Daily order, customer, product revenue, freight, and review score summary.",
        order_by="order_date",
    ),
    MartExport(
        name="payment_mix_summary",
        source_name="payment_mix_summary",
        file_name="payment_mix_summary.csv",
        description="Daily payment type, installment, order, and payment-value mix.",
        order_by="order_date, payment_type",
    ),
    MartExport(
        name="review_delivery_drivers",
        source_name="review_delivery_drivers",
        file_name="review_delivery_drivers.csv",
        description="Review-score buckets with delivery duration and late-delivery rate.",
        order_by="review_score",
    ),
    MartExport(
        name="seller_sla_summary",
        source_name="seller_sla_summary",
        file_name="seller_sla_summary.csv",
        description="Seller SLA, revenue, delivery, item, and review metrics.",
        order_by="product_revenue DESC",
    ),
    MartExport(
        name="seller_risk_scorecard",
        source_name="seller_risk_scorecard",
        file_name="seller_risk_scorecard.csv",
        description="Seller priority score from SLA, review, cancellation, lane, and volume signals.",
        order_by="risk_score DESC, product_revenue DESC",
    ),
    MartExport(
        name="category_performance_summary",
        source_name="category_performance_summary",
        file_name="category_performance_summary.csv",
        description="Category revenue, freight, review, and delivery-quality summary.",
        order_by="product_revenue DESC",
    ),
    MartExport(
        name="location_service_level_summary",
        source_name="location_service_level_summary",
        file_name="location_service_level_summary.csv",
        description="Customer-state and seller-state service-level lanes with coordinate coverage.",
        order_by="orders DESC",
    ),
    MartExport(
        name="customer_cohort_retention",
        source_name="customer_cohort_retention",
        file_name="customer_cohort_retention.csv",
        description="Customer repeat-purchase cohort retention matrix.",
        order_by="cohort_month, months_since_first_order",
    ),
)


def _assert_readable_database(database_url: str):
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite":
        return
    if url.database in {None, "", ":memory:"}:
        return

    db_path = Path(url.database).expanduser()
    if not db_path.exists():
        raise FileNotFoundError(
            f"SQLite database not found: {db_path}. Run ingestion before BI export."
        )


def _safe_identifier(identifier: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", identifier):
        raise ValueError(f"Unsafe SQL identifier: {identifier}")
    return identifier


def _select_marts(names: Sequence[str] | None = None) -> list[MartExport]:
    if not names:
        return list(BI_MARTS)

    selected = set(names)
    known = {mart.name for mart in BI_MARTS}
    unknown = sorted(selected - known)
    if unknown:
        raise ValueError(f"Unknown mart export(s): {', '.join(unknown)}")
    return [mart for mart in BI_MARTS if mart.name in selected]


def _available_relations(engine) -> set[str]:
    inspector = inspect(engine)
    return set(inspector.get_table_names()) | set(inspector.get_view_names())


def _read_mart(conn, mart: MartExport, limit: int | None = None) -> pd.DataFrame:
    source_name = _safe_identifier(mart.source_name)
    query = f"SELECT * FROM {source_name}"
    if mart.order_by:
        query = f"{query} ORDER BY {mart.order_by}"
    if limit is not None:
        query = f"{query} LIMIT :limit"
        return pd.read_sql(text(query), conn, params={"limit": limit})
    return pd.read_sql(text(query), conn)


def export_bi_marts(
    database_url: str,
    output_dir: Path,
    marts: Sequence[MartExport] | None = None,
    *,
    strict: bool = False,
    limit: int | None = None,
) -> dict:
    """Write selected BI marts as CSV files and return a manifest."""
    _assert_readable_database(database_url)
    output_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(database_url)
    selected_marts = list(marts or BI_MARTS)
    manifest = {
        "status": "ok",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "database_backend": engine.url.get_backend_name(),
        "output_dir": str(output_dir),
        "exports": [],
    }

    with engine.connect() as conn:
        available_relations = _available_relations(engine)
        for mart in selected_marts:
            export_record = {
                **asdict(mart),
                "status": "pending",
                "rows": 0,
                "columns": [],
            }
            if mart.source_name not in available_relations:
                export_record["status"] = "skipped"
                export_record["reason"] = f"Missing source relation: {mart.source_name}"
                manifest["exports"].append(export_record)
                if strict:
                    raise RuntimeError(export_record["reason"])
                continue

            try:
                frame = _read_mart(conn, mart, limit=limit)
                output_path = output_dir / mart.file_name
                frame.to_csv(output_path, index=False)
                export_record.update(
                    {
                        "status": "exported",
                        "rows": int(len(frame)),
                        "columns": list(frame.columns),
                        "path": str(output_path),
                    }
                )
            except Exception as exc:
                export_record["status"] = "failed"
                export_record["reason"] = str(exc)
                if strict:
                    raise
            finally:
                manifest["exports"].append(export_record)

    if any(item["status"] != "exported" for item in manifest["exports"]):
        manifest["status"] = "partial"

    manifest_path = output_dir / "manifest.json"
    manifest["manifest_path"] = str(manifest_path)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export local BI-ready Olist mart CSVs.")
    parser.add_argument("--database-url", default=DATABASE_URL)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "exports" / "bi",
        help="Local output directory. Defaults under ignored data/.",
    )
    parser.add_argument(
        "--mart",
        action="append",
        choices=[mart.name for mart in BI_MARTS],
        help="Export only this mart. Repeat for multiple marts.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Optional per-mart row limit.")
    parser.add_argument("--strict", action="store_true", help="Fail on missing or failed exports.")
    parser.add_argument(
        "--apply-views",
        action="store_true",
        help="Apply sql/views before exporting. Useful after fresh ingestion.",
    )
    parser.add_argument(
        "--replace-views",
        action="store_true",
        help="Drop and recreate views when --apply-views is set.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    _assert_readable_database(args.database_url)

    if args.apply_views:
        applied, skipped = apply_sql_views(
            database_url=args.database_url,
            sql_dir=PROJECT_ROOT / "sql" / "views",
            strict=args.strict,
            replace=args.replace_views,
        )
        print(f"[views] applied={len(applied)} skipped={len(skipped)}")

    manifest = export_bi_marts(
        database_url=args.database_url,
        output_dir=args.output_dir,
        marts=_select_marts(args.mart),
        strict=args.strict,
        limit=args.limit,
    )
    exported = sum(1 for item in manifest["exports"] if item["status"] == "exported")
    skipped = sum(1 for item in manifest["exports"] if item["status"] == "skipped")
    failed = sum(1 for item in manifest["exports"] if item["status"] == "failed")
    print(
        f"[bi-export] status={manifest['status']} exported={exported} "
        f"skipped={skipped} failed={failed} manifest={manifest['manifest_path']}"
    )
    return 0 if manifest["status"] == "ok" or not args.strict else 1


if __name__ == "__main__":
    raise SystemExit(main())
