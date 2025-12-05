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
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")

# Fallback for local execution if 'db' is not resolvable
import socket
try:
    if POSTGRES_HOST == "db":
        socket.gethostbyname("db")
except socket.error:
    print("⚠️ Host 'db' not found, falling back to 'localhost'")
    POSTGRES_HOST = "localhost"
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "olist")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# MLflow Configuration
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")

# API Configuration
# Dashboard -> API connection
API_URL = os.getenv("API_URL", "http://api:8000")
