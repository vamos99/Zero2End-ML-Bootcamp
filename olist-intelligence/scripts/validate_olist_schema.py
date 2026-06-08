"""Validate local Olist CSV files or an ingested database against Kaggle schema."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.config import DATABASE_URL, DATA_RAW_PATH  # noqa: E402
from src.data_contract import (  # noqa: E402
    KAGGLE_DATASET_URL,
    expected_column_count,
    validate_csv_directory,
    validate_database_schema,
)


def _print_issues(issues):
    for issue in issues:
        print(f"[fail] {issue.scope}:{issue.name}:{issue.issue} -> {issue.details}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Olist source schema.")
    parser.add_argument(
        "--target",
        choices=("csv", "db", "both"),
        default="both",
        help="Validate raw CSV headers, database tables, or both.",
    )
    parser.add_argument(
        "--data-path",
        default=str(DATA_RAW_PATH),
        help="Directory containing raw Kaggle Olist CSV files.",
    )
    parser.add_argument(
        "--database-url",
        default=DATABASE_URL,
        help="SQLAlchemy database URL for an ingested Olist database.",
    )
    parser.add_argument(
        "--strict-extra",
        action="store_true",
        help="Fail when extra columns are present. Missing required columns always fail.",
    )
    args = parser.parse_args()

    issues = []

    if args.target in {"csv", "both"}:
        issues.extend(validate_csv_directory(Path(args.data_path), strict_extra=args.strict_extra))

    if args.target in {"db", "both"}:
        issues.extend(validate_database_schema(args.database_url, strict_extra=args.strict_extra))

    if issues:
        print(
            "[schema] Olist source contract mismatch. "
            f"Expected Kaggle source: {KAGGLE_DATASET_URL}"
        )
        _print_issues(issues)
        return 1

    print(
        "[schema] ok: validated 9 Kaggle CSV contracts "
        f"and {expected_column_count()} expected source columns"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
