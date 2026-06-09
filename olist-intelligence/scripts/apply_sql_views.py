"""Apply reusable analytics SQL views to the configured database."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.config import DATABASE_URL  # noqa: E402


def iter_sql_files(sql_dir: Path):
    return sorted(sql_dir.glob("*.sql"))


def _view_name_from_file(sql_file: Path) -> str:
    view_name = sql_file.stem
    if not view_name.replace("_", "").isalnum():
        raise ValueError(f"Unsafe SQL view file name: {sql_file.name}")
    return view_name


def apply_sql_views(database_url: str, sql_dir: Path, strict: bool = False, replace: bool = False):
    engine = create_engine(database_url)
    applied = []
    skipped = []

    with engine.begin() as conn:
        for sql_file in iter_sql_files(sql_dir):
            statement = sql_file.read_text(encoding="utf-8").strip()
            if not statement:
                continue

            try:
                if replace:
                    conn.execute(text(f"DROP VIEW IF EXISTS {_view_name_from_file(sql_file)}"))
                conn.execute(text(statement))
                applied.append(sql_file.name)
            except Exception as exc:
                if strict:
                    raise
                skipped.append((sql_file.name, str(exc)))

    return applied, skipped


def main():
    parser = argparse.ArgumentParser(description="Apply analytics SQL views.")
    parser.add_argument(
        "--sql-dir",
        default=str(PROJECT_ROOT / "sql" / "views"),
        help="Directory containing .sql view files.",
    )
    parser.add_argument(
        "--database-url",
        default=DATABASE_URL,
        help="SQLAlchemy database URL. Defaults to src.config.DATABASE_URL.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on the first SQL error instead of reporting skipped views.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Drop each target view before applying the SQL file.",
    )
    args = parser.parse_args()

    applied, skipped = apply_sql_views(
        database_url=args.database_url,
        sql_dir=Path(args.sql_dir),
        strict=args.strict,
        replace=args.replace,
    )

    for name in applied:
        print(f"[ok] applied {name}")

    for name, error in skipped:
        print(f"[skip] {name}: {error}")

    print(f"applied={len(applied)} skipped={len(skipped)}")


if __name__ == "__main__":
    main()
