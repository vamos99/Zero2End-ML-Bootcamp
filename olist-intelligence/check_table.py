import pandas as pd
from sqlalchemy import create_engine, text
from src.config import DATABASE_URL

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1 FROM order_reviews LIMIT 1"))
        print("ORDER_REVIEWS_EXISTS")
except Exception as e:
    print(f"ERROR: {e}")
