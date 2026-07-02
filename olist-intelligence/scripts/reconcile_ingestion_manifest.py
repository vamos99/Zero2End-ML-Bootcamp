"""Reconcile an ingestion manifest against the current database."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.config import DATABASE_URL  # noqa: E402
from src.ml.ingest import reconcile_ingestion_manifest  # noqa: E402


DEFAULT_MANIFEST_PATH = PROJECT_ROOT / "data" / "processed" / "ingestion_manifest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile Olist ingestion manifest row counts.")
    parser.add_argument("--database-url", default=DATABASE_URL)
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST_PATH)
    args = parser.parse_args()

    if not args.manifest_path.exists():
        print(f"[manifest] missing: {args.manifest_path}")
        return 1

    result = reconcile_ingestion_manifest(args.database_url, args.manifest_path)
    if result["issues"]:
        print(
            f"[manifest] failed: run_id={result['run_id']}; "
            f"checked_tables={result['checked_tables']}"
        )
        for issue in result["issues"]:
            print(
                "[fail] "
                f"{issue['table_name']}: source_rows={issue['source_rows']} "
                f"db_rows={issue['db_rows']}"
            )
        return 1

    print(
        f"[manifest] ok: run_id={result['run_id']}; "
        f"checked_tables={result['checked_tables']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
