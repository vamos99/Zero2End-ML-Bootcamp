from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.config import DATABASE_URL

# Database Setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# FastAPI App
app = FastAPI(
    title="Olist Intelligence API",
    description="API for Logistics Predictions and Customer Churn Risk",
    version="1.0.0"
)

# Pydantic Models
class LogisticsPrediction(BaseModel):
    order_id: str
    customer_id: str
    predicted_delivery_days: float
    actual_delivery_days: float | None = None

class CustomerSegment(BaseModel):
    customer_unique_id: str
    recency: float
    frequency: float
    monetary: float
    cluster: int
    segment: str

# Endpoints

@app.get("/")
def read_root():
    return {"message": "Welcome to Olist Intelligence API "}

@app.get("/orders/{order_id}/prediction", response_model=LogisticsPrediction)
def get_order_prediction(order_id: str, db: Session = Depends(get_db)):
    """
    Get logistics prediction for a specific order.
    """
    query = text("SELECT order_id, customer_id, predicted_delivery_days, delivery_days FROM logistics_predictions WHERE order_id = :order_id")
    result = db.execute(query, {"order_id": order_id}).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Order prediction not found")
    
    return LogisticsPrediction(
        order_id=result[0],
        customer_id=result[1],
        predicted_delivery_days=result[2],
        actual_delivery_days=result[3]
    )

@app.get("/customers/{customer_unique_id}/segment", response_model=CustomerSegment)
def get_customer_segment(customer_unique_id: str, db: Session = Depends(get_db)):
    """
    Get segment info for a specific customer.
    """
    query = text("SELECT customer_unique_id, \"Recency\", \"Frequency\", \"Monetary\", \"Cluster\", \"Segment\" FROM customer_segments WHERE customer_unique_id = :id")
    result = db.execute(query, {"id": customer_unique_id}).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Customer segment not found")
    
    return CustomerSegment(
        customer_unique_id=result[0],
        recency=result[1],
        frequency=result[2],
        monetary=result[3],
        cluster=result[4],
        segment=result[5]
    )

@app.post("/predict/delivery")
def predict_delivery_mock():
    """
    Mock endpoint for real-time delivery prediction.
    In a real scenario, this would load the CatBoost model.
    """
    return {
        "predicted_days": 5.4,
        "risk_level": "Low",
        "note": "This is a mock prediction for demonstration."
    }

@app.post("/predict/churn")
def predict_churn_mock():
    """
    Mock endpoint for real-time churn prediction.
    In a real scenario, this would load the XGBoost/CatBoost model.
    """
    return {
        "churn_probability": 0.25,
        "risk_level": "Medium",
        "note": "This is a mock prediction for demonstration."
    }
