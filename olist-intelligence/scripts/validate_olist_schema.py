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
    validate_database_quality,
    validate_database_schema,
    validate_generated_outputs,
)


def _print_issues(issues):
    for issue in issues:
        print(f"[fail] {issue.scope}:{issue.name}:{issue.issue} -> {issue.details}")


def _selected_checks(target: str) -> list[str]:
    if target == "csv":
        return ["csv"]
    if target == "db":
        return ["db_schema"]
    if target == "quality":
        return ["db_quality"]
    if target == "generated":
        return ["generated_outputs"]
    if target == "both":
        return ["csv", "db_schema"]
    return ["csv", "db_schema", "db_quality", "generated_outputs"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Olist source schema.")
    parser.add_argument(
        "--target",
        choices=("csv", "db", "quality", "generated", "both", "all"),
        default="both",
        help="Validate raw CSV headers, database schema, database quality checks, or all checks.",
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

    db_schema_issues = []

    if args.target in {"csv", "both", "all"}:
        issues.extend(validate_csv_directory(Path(args.data_path), strict_extra=args.strict_extra))

    if args.target in {"db", "both", "all"}:
        db_schema_issues = validate_database_schema(
            args.database_url,
            strict_extra=args.strict_extra,
        )
        issues.extend(db_schema_issues)

    if args.target == "quality":
        issues.extend(validate_database_quality(args.database_url))

    if args.target == "generated":
        issues.extend(validate_generated_outputs(args.database_url))

    if args.target == "all" and not db_schema_issues:
        issues.extend(validate_database_quality(args.database_url))
        issues.extend(validate_generated_outputs(args.database_url))

    if issues:
        print(
            "[schema] Olist source contract mismatch. "
            f"Expected Kaggle source: {KAGGLE_DATASET_URL}"
        )
        _print_issues(issues)
        return 1

    print(
        f"[schema] ok: target={args.target}; "
        f"checks={', '.join(_selected_checks(args.target))}; "
        "source_contract=9_csv_files; "
        f"required_columns={expected_column_count()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
