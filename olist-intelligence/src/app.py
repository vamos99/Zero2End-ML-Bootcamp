from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
import os
import sys
from pathlib import Path
import pickle
from contextlib import asynccontextmanager
from src.config import DATABASE_URL, MODELS_PATH
import pandas as pd

# Add project root to path
# (Required for local debugging if running script directly)
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# ============== API KEY SECURITY ==============
API_KEY = os.getenv("API_KEY", "olist-dev-key-2024")  # Default for development
api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    """Verify API key for protected endpoints."""
    if api_key is None or api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")
    return api_key

# ============================================

# Database Setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load Models on Startup
    try:
        with open(MODELS_PATH / "logistics_model.pkl", "rb") as f:
            models["logistics"] = pickle.load(f)
        with open(MODELS_PATH / "churn_model.pkl", "rb") as f:
            models["churn"] = pickle.load(f)
        with open(MODELS_PATH / "recommender_model.pkl", "rb") as f:
            models["recommender"] = pickle.load(f)
        print("✅ Models loaded successfully")
    except Exception as e:
        print(f"⚠️ Failed to load models: {e}")
    yield
    models.clear()

# ... (Previous Code)



# FastAPI App
app = FastAPI(
    title="Olist Intelligence API",
    description="API for Logistics Predictions and Customer Churn Risk",
    version="2.0.0", # Real Inference Update
    lifespan=lifespan
)

# ... (Previous Pydantic Models)

class DeliveryInput(BaseModel):
    freight_value: float
    price: float
    product_weight_g: float
    product_description_lenght: float

class ChurnInput(BaseModel):
    Recency: float
    Frequency: float
    Monetary: float

# ... (Previous Endpoints)

@app.post("/predict/delivery")
def predict_delivery(data: DeliveryInput):
    """
    Real-time delivery duration prediction using CatBoost.
    """
    if "logistics" not in models:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    # Prepare DataFrame
    df = pd.DataFrame([data.model_dump()])
    
    # Predict
    prediction = models["logistics"].predict(df)[0]
    
    return {
        "predicted_days": float(prediction),
        "risk_level": "High" if prediction > 10 else "Low"
    }

@app.post("/predict/churn")
def predict_churn(data: ChurnInput):
    """
    Real-time churn risk prediction.
    """
    if "churn" not in models:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    # Prepare DataFrame
    df = pd.DataFrame([data.model_dump()])
    
    # Predict Class (1 = Risk)
    prediction = models["churn"].predict(df)[0]
    prob = models["churn"].predict_proba(df)[0][1]
    
    return {
        "is_churn_risk": bool(prediction),
        "churn_probability": float(prob),
        "risk_level": "Critical" if prob > 0.7 else "Medium" if prob > 0.4 else "Low"
    }

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
    cluster: int
    segment: str

class RecommendationInput(BaseModel):
    customer_id: str
    top_k: int = 5

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

@app.post("/recommend")
def recommend_products(data: RecommendationInput):
    """
    Personalized Product Recommendation using SVD (Collaborative Filtering).
    """
    if "recommender" not in models:
        raise HTTPException(status_code=503, detail="Recommender model not loaded")
    
    artifact = models["recommender"]
    user_map = artifact["user_map"]
    reverse_product_map = artifact["reverse_product_map"]
    matrix_reduced = artifact["matrix_reduced"]
    product_components = artifact["product_components"]
    
    # 1. Check if user exists (Cold Start Check)
    if data.customer_id not in user_map:
        return {
            "customer_id": data.customer_id,
            "recommendations": ["auto_best_seller_1", "auto_best_seller_2"], # Placeholder for popularity fallback
            "method": "popularity_fallback (User Unknown)"
        }
        
    # 2. Get User Vector
    user_idx = user_map[data.customer_id]
    user_vector = matrix_reduced[user_idx] # Shape: (n_components,)
    
    # 3. Compute Scores (Dot Product)
    # user_vector (20,) @ product_components (20, n_products) -> scores (n_products,)
    scores = user_vector @ product_components
    
    # 4. Get Top K Indices
    # argsort returns indices that would sort the array, we take last K and reverse
    top_indices = scores.argsort()[-data.top_k:][::-1]
    
    # 5. Map back to Product IDs
    recommended_products = [reverse_product_map[i] for i in top_indices]
    
    return {
        "customer_id": data.customer_id,
        "recommendations": recommended_products,
        "method": "personalized_svd"
    }
