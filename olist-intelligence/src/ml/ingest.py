import os
import glob
import json
import pandas as pd
import polars as pl
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.engine import make_url
from typing import List
import logging
from tenacity import before_log, retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from src.config import DATABASE_URL, DATA_RAW_PATH
from src.data_contract import (
    EXPECTED_CSV_SCHEMAS,
    table_name_from_csv,
    validate_csv_directory,
    validate_database_quality,
    validate_database_schema,
)
from pathlib import Path

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _safe_database_target(db_url: str) -> dict:
    url = make_url(db_url)
    target = {"driver": url.drivername}
    if url.drivername.startswith("sqlite"):
        target["database"] = Path(url.database or "").name
    else:
        target["host"] = url.host
        target["database"] = url.database
    return {key: value for key, value in target.items() if value}


def _safe_table_name(table_name: str) -> str:
    if not table_name.replace("_", "").isalnum():
        raise ValueError(f"Unsafe table name in ingestion manifest: {table_name}")
    return table_name


def reconcile_ingestion_manifest(db_url: str, manifest_path: str | Path) -> dict:
    """Compare manifest source rows with current database table row counts."""
    path = Path(manifest_path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    engine = create_engine(db_url)
    issues = []
    checked_tables = 0

    with engine.connect() as conn:
        for table in manifest.get("tables", []):
            table_name = _safe_table_name(table["table_name"])
            expected_rows = int(table["source_rows"])
            actual_rows = int(
                conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar_one()
            )
            checked_tables += 1
            if actual_rows != expected_rows:
                issues.append({
                    "table_name": table_name,
                    "source_rows": expected_rows,
                    "db_rows": actual_rows,
                    "issue": "row_count_mismatch",
                })

    return {
        "run_id": manifest.get("run_id"),
        "status": "ok" if not issues else "failed",
        "checked_tables": checked_tables,
        "issues": issues,
    }


class OlistIngestor:
    """
    Handles the ingestion of raw CSV files into the Database (SQLite).
    Includes automatic downloading from Kaggle if data is missing.
    """
    
    KAGGLE_DATASET = "olistbr/brazilian-ecommerce"
    
    def __init__(self, db_url: str, data_path: str, manifest_path: str | None = None):
        self.db_url = db_url
        self.data_path = Path(data_path)
        self.project_root = Path(__file__).resolve().parents[2]
        self.engine = create_engine(self.db_url)
        self.manifest_path = (
            Path(manifest_path)
            if manifest_path
            else self.project_root / "data" / "processed" / "ingestion_manifest.json"
        )

    def download_from_kaggle(self):
        """Downloads dataset from Kaggle if not present."""
        
        # Check credentials
        if not (os.getenv("KAGGLE_USERNAME") and os.getenv("KAGGLE_KEY")):
            # Look for kaggle.json in standard paths? Kaggle lib does this.
            # But users might assume it works without setup.
            logger.info("ℹ️ Kaggle credentials env vars not found. Assuming local kaggle.json config or manual download.")
            pass # Kaggle lib will autodetect ~/.kaggle/kaggle.json

        # Cleanup potential corrupted files before retry
        zip_file = self.data_path / "brazilian-ecommerce.zip"
        if zip_file.exists():
            zip_file.unlink()
            logger.info("🗑️ Removed existing zip file to ensure fresh download.")

        try:
            import kaggle
            logger.info(f"⬇️ Downloading {self.KAGGLE_DATASET} from Kaggle...")
            
            # Authenticate (uses env vars or ~/.kaggle/kaggle.json)
            kaggle.api.authenticate()
            
            # Download to data path
            kaggle.api.dataset_download_files(
                self.KAGGLE_DATASET, 
                path=self.data_path, 
                unzip=True
            )
            logger.info("✅ Download complete.")
            
        except ImportError:
            logger.error("❌ 'kaggle' library not installed. Add it to requirements.txt.")
            raise
        except Exception as e:
            if zip_file.exists():
                zip_file.unlink()
                logger.info("Removed corrupted zip file.")
            raise RuntimeError(
                "Kaggle download failed. Configure Kaggle credentials or place the 9 CSV files manually."
            ) from e

    def load_predictions_from_csv(self):
        """Loads pre-calculated predictions if available (Streamlit Cloud support)."""
        try:
            processed_dir = self.project_root / "data" / "processed"
            
            # 1. Logistics Predictions
            log_path = processed_dir / "logistics_predictions.csv"
            if log_path.exists():
                print(f"📦 Loading pre-calculated logistics predictions from {log_path}...")
                df_log = pd.read_csv(log_path)
                df_log.to_sql("logistics_predictions", self.engine, if_exists="replace", index=False)
                print("✅ Service restored: Logistics Engine")
            
            # 2. Customer Segments
            seg_path = processed_dir / "customer_segments.csv"
            if seg_path.exists():
                print(f"📊 Loading pre-calculated customer segments from {seg_path}...")
                df_seg = pd.read_csv(seg_path)
                df_seg.to_sql("customer_segments", self.engine, if_exists="replace", index=False)
                print("✅ Service restored: Growth Engine")
                
        except Exception as e:
            logger.warning("Optional static prediction load failed: %s", e)

    def get_csv_files(self) -> List[str]:
        """Scans the data directory for CSV files. Downloads if empty."""
        
        if not self.data_path.exists():
            self.data_path.mkdir(parents=True, exist_ok=True)
            
        search_pattern = str(self.data_path / "*.csv")
        files = glob.glob(search_pattern)
        
        if not files:
            logger.warning(f"No CSV files found in {self.data_path}. Attempting download...")
            self.download_from_kaggle()
            files = glob.glob(search_pattern)

        if not files:
            raise FileNotFoundError(f"No Olist CSV files found in {self.data_path}")

        issues = validate_csv_directory(self.data_path)
        if issues:
            summary = "; ".join(f"{issue.name}:{issue.issue}" for issue in issues[:5])
            raise ValueError(f"Olist CSV contract validation failed: {summary}")

        return sorted(files)

    def _extract_table_name(self, file_path: str) -> str:
        """Extracts a clean table name from the filename."""
        file_name = os.path.basename(file_path)
        return table_name_from_csv(file_name)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type((OperationalError, ConnectionError)),
        before=before_log(logger, logging.INFO),
        reraise=True,
    )
    def ingest_file(self, file_path: str):
        """Reads a single CSV and writes it to the database."""
        table_name = self._extract_table_name(file_path)
        file_name = os.path.basename(file_path)
        logger.info(f"Processing {file_name} -> Table: {table_name}")

        df = pl.read_csv(file_path)
        df.write_database(
            table_name=table_name,
            connection=self.engine,
            if_table_exists="replace",
            engine="sqlalchemy",
        )
        db_rows = self._table_row_count(table_name)
        expected_columns = EXPECTED_CSV_SCHEMAS.get(file_name, [])
        missing_columns = [column for column in expected_columns if column not in df.columns]
        logger.info("Successfully wrote %s rows to '%s'", db_rows, table_name)
        return {
            "file_name": file_name,
            "table_name": table_name,
            "source_rows": int(df.shape[0]),
            "db_rows": db_rows,
            "missing_columns": missing_columns,
            "status": "loaded" if not missing_columns and int(df.shape[0]) == db_rows else "warning",
        }

    def _table_row_count(self, table_name: str) -> int:
        safe_name = _safe_table_name(table_name)
        with self.engine.connect() as conn:
            return int(conn.execute(text(f"SELECT COUNT(*) FROM {safe_name}")).scalar_one())

    def write_ingestion_manifest(self, tables: list[dict], status: str = "success") -> Path:
        """Write a local manifest for row-count reconciliation after ingest."""
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest = {
            "run_id": _utc_run_id(),
            "status": status,
            "source_path": str(self.data_path),
            "database_target": _safe_database_target(self.db_url),
            "tables": tables,
        }
        self.manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        logger.info("Wrote ingestion manifest: %s", self.manifest_path)
        return self.manifest_path

    def run(self):
        """Executes the full ingestion process."""
        logger.info("🚀 Starting Data Ingestion Process...")
        
        # Check if DB is SQLite and already exists (Optimization)
        if "sqlite" in self.db_url:
            db_file = self.db_url.replace("sqlite:///", "")
            if os.path.exists(db_file) and not os.getenv("FORCE_INGEST"):
                schema_issues = validate_database_schema(self.db_url)
                if not schema_issues:
                    logger.info("Validated SQLite DB '%s'. Skipping ingestion.", db_file)
                    return
                logger.warning("Existing SQLite DB failed schema validation; rebuilding it.")

        csv_files = self.get_csv_files()
        manifest_tables = []
        
        for file_path in csv_files:
            manifest_tables.append(self.ingest_file(file_path))

        quality_issues = validate_database_quality(self.db_url)
        if quality_issues:
            summary = "; ".join(f"{issue.name}:{issue.issue}" for issue in quality_issues[:5])
            raise RuntimeError(f"Ingested database quality validation failed: {summary}")

        self.load_predictions_from_csv()
        self.write_ingestion_manifest(manifest_tables)
        logger.info("Data ingestion complete.")

if __name__ == "__main__":
    ingestor = OlistIngestor(db_url=DATABASE_URL, data_path=str(DATA_RAW_PATH))
    ingestor.run()
