import os
import glob
import pandas as pd
import polars as pl
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from typing import List
import logging
from tenacity import before_log, retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from src.config import DATABASE_URL, DATA_RAW_PATH
from src.data_contract import (
    table_name_from_csv,
    validate_csv_directory,
    validate_database_quality,
    validate_database_schema,
)
from pathlib import Path

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OlistIngestor:
    """
    Handles the ingestion of raw CSV files into the Database (SQLite).
    Includes automatic downloading from Kaggle if data is missing.
    """
    
    KAGGLE_DATASET = "olistbr/brazilian-ecommerce"
    
    def __init__(self, db_url: str, data_path: str):
        self.db_url = db_url
        self.data_path = Path(data_path)
        self.project_root = self.data_path.parent.parent
        self.engine = create_engine(self.db_url)

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
        logger.info(f"Processing {os.path.basename(file_path)} -> Table: {table_name}")

        df = pl.read_csv(file_path)
        df.write_database(
            table_name=table_name,
            connection=self.engine,
            if_table_exists="replace",
            engine="sqlalchemy",
        )
        logger.info("Successfully wrote %s rows to '%s'", df.shape[0], table_name)

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
        
        for file_path in csv_files:
            self.ingest_file(file_path)

        quality_issues = validate_database_quality(self.db_url)
        if quality_issues:
            summary = "; ".join(f"{issue.name}:{issue.issue}" for issue in quality_issues[:5])
            raise RuntimeError(f"Ingested database quality validation failed: {summary}")

        self.load_predictions_from_csv()
        logger.info("Data ingestion complete.")

if __name__ == "__main__":
    ingestor = OlistIngestor(db_url=DATABASE_URL, data_path=str(DATA_RAW_PATH))
    ingestor.run()
