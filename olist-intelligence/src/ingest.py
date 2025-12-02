import os
import glob
import polars as pl
from sqlalchemy import create_engine
from typing import List
import logging

# Import configuration
try:
    from config import DATABASE_URL, DATA_RAW_PATH
except ImportError:
    # Fallback if running from root without module context
    from src.config import DATABASE_URL, DATA_RAW_PATH

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OlistIngestor:
    """
    Handles the ingestion of raw CSV files into the PostgreSQL database.
    Follows SRP: Only responsible for ingestion logic.
    """
    
    def __init__(self, db_url: str, data_path: str):
        self.db_url = db_url
        self.data_path = data_path
        self.engine = create_engine(self.db_url)

    def get_csv_files(self) -> List[str]:
        """Scans the data directory for CSV files."""
        search_pattern = os.path.join(self.data_path, "*.csv")
        files = glob.glob(search_pattern)
        if not files:
            logger.warning(f"No CSV files found in {self.data_path}")
        return files

    def _extract_table_name(self, file_path: str) -> str:
        """Extracts a clean table name from the filename."""
        file_name = os.path.basename(file_path)
        # Remove prefix and extension
        clean_name = file_name.replace("olist_", "").replace("_dataset.csv", "").replace(".csv", "")
        return clean_name

    def ingest_file(self, file_path: str):
        """Reads a single CSV and writes it to the database."""
        table_name = self._extract_table_name(file_path)
        logger.info(f"Processing {os.path.basename(file_path)} -> Table: {table_name}")

        try:
            # Read with Polars (Fast & Memory Efficient)
            df = pl.read_csv(file_path, ignore_errors=True)
            
            # Write to Database
            # Note: Polars write_database uses SQLAlchemy engine
            df.write_database(
                table_name=table_name,
                connection=self.db_url,
                if_table_exists="replace",
                engine="sqlalchemy"
            )
            logger.info(f"✅ Successfully wrote {df.shape[0]} rows to '{table_name}'")

        except Exception as e:
            logger.error(f"❌ Failed to ingest {file_path}: {e}")

    def run(self):
        """Executes the full ingestion process."""
        logger.info("🚀 Starting Data Ingestion Process...")
        csv_files = self.get_csv_files()
        
        for file_path in csv_files:
            self.ingest_file(file_path)
        
        logger.info("✨ Data Ingestion Complete.")

if __name__ == "__main__":
    # Dependency Injection via Constructor
    ingestor = OlistIngestor(db_url=DATABASE_URL, data_path=str(DATA_RAW_PATH))
    ingestor.run()
