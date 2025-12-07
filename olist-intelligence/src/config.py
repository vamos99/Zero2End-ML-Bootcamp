import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project Paths
# src/config.py -> src/ -> olist-intelligence/
PROJECT_ROOT = Path(__file__).parent.parent
DATA_RAW_PATH = PROJECT_ROOT / "data" / "raw"
MODELS_PATH = PROJECT_ROOT / "models"

# Database Configuration
# Default to SQLite for portability, allows override via Env Var (e.g. for Docker/Postgres)
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "olist")

if os.getenv("DATABASE_URL"):
    DATABASE_URL = os.getenv("DATABASE_URL")
elif os.getenv("POSTGRES_HOST") == "db": # Docker explicit
    DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
else:
    # Default: SQLite (Local file)
    db_path = PROJECT_ROOT / "olist.db"
    DATABASE_URL = f"sqlite:///{db_path}"

# MLflow Configuration
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")

# API Configuration
# Dashboard -> API connection
API_URL = os.getenv("API_URL", "http://api:8000")
