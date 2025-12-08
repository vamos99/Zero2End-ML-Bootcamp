import os
import glob
import polars as pl
from sqlalchemy import create_engine
from typing import List
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, before_log
from src.config import DATABASE_URL, DATA_RAW_PATH
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
            print(f"❌ Failed to download from Kaggle: {e}")
            print("👉 Please set KAGGLE_USERNAME and KAGGLE_KEY environment variables.")
            # Don't crash immediately, functionality might be limited
            
            # Cleanup bad file
            if zip_file.exists():
                zip_file.unlink()
                logger.info("🗑️ Removed corrupted zip file.")
            pass

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
            
        return files

    def _extract_table_name(self, file_path: str) -> str:
        """Extracts a clean table name from the filename."""
        file_name = os.path.basename(file_path)
        clean_name = file_name.replace("olist_", "").replace("_dataset.csv", "").replace(".csv", "")
        return clean_name

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10), before=before_log(logger, logging.INFO))
    def ingest_file(self, file_path: str):
        """Reads a single CSV and writes it to the database."""
        table_name = self._extract_table_name(file_path)
        logger.info(f"Processing {os.path.basename(file_path)} -> Table: {table_name}")

        try:
            # Read with Polars
            df = pl.read_csv(file_path, ignore_errors=True)
            
            # Write to Database
            # SQLite connection string handling for Polars might differ, relying on SQLAlchemy connector
            df.write_database(
                table_name=table_name,
                connection=self.engine, # Polars accepts engine object too
                if_table_exists="replace",
                engine="sqlalchemy"
            )
            logger.info(f"✅ Successfully wrote {df.shape[0]} rows to '{table_name}'")

        except Exception as e:
            logger.error(f"❌ Failed to ingest {file_path}: {e}")

    def load_predictions_from_csv(self):
        """Loads pre-calculated predictions if available (Streamlit Cloud support)."""
        try:
            processed_dir = self.data_path.parent / "processed"
            
            # 1. Logistics Predictions
            log_path = processed_dir / "logistics_predictions.csv"
            if log_path.exists():
                logger.info(f"📦 Loading pre-calculated logistics predictions from {log_path}...")
                df_log = pl.read_csv(log_path).to_pandas()
                df_log.to_sql("logistics_predictions", self.engine, if_exists="replace", index=False)
                logger.info("✅ Service restored: Logistics Engine")
            
            # 2. Customer Segments
            seg_path = processed_dir / "customer_segments.csv"
            if seg_path.exists():
                logger.info(f"📊 Loading pre-calculated customer segments from {seg_path}...")
                df_seg = pl.read_csv(seg_path).to_pandas()
                df_seg.to_sql("customer_segments", self.engine, if_exists="replace", index=False)
                logger.info("✅ Service restored: Growth Engine")
                
        except Exception as e:
            logger.error(f"⚠️ Failed to load static predictions: {e}")

    def run(self):
        """Executes the full ingestion process."""
        logger.info("🚀 Starting Data Ingestion Process...")
        
        # Check if DB is SQLite and already exists (Optimization)
        if "sqlite" in self.db_url:
            db_file = self.db_url.replace("sqlite:///", "")
            if os.path.exists(db_file) and os.path.getsize(db_file) > 1000: # Simple check
                 logger.info(f"ℹ️ SQLite DB '{db_file}' already exists. Skipping ingestion.")
                 # IMPORTANT: Return here to start faster. 
                 # Set FORCE_INGEST=1 env var to override.
                 if not os.getenv("FORCE_INGEST"):
                     return

        csv_files = self.get_csv_files()
        
        if not csv_files:
            logger.error("❌ No data found and download failed. Getting data is required.")
            return

        for file_path in csv_files:
            self.ingest_file(file_path)
        
        self.load_predictions_from_csv()
        logger.info("✨ Data Ingestion Complete.")

if __name__ == "__main__":
    ingestor = OlistIngestor(db_url=DATABASE_URL, data_path=str(DATA_RAW_PATH))
    ingestor.run()
