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
        from src.ml.registry import load_production_model
        
        # Load Logistics (CatBoost)
        try:
            models["logistics"] = load_production_model("logistics", flavor="catboost")
        except Exception as e:
            print(f"Failed to load logistics: {e}")

        # Load Churn (CatBoost)
        try:
            models["churn"] = load_production_model("churn", flavor="catboost")
        except Exception as e:
            print(f"Failed to load churn: {e}")

        # Load Recommender (Dict - Local Fallback usually)
        try:
            # Recommender is not fully in Registry yet, uses local fallback path in registry
            models["recommender"] = load_production_model("recommender", flavor="sklearn")
        except Exception as e:
            print(f"Failed to load recommender: {e}")
            
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
    """10-Feature Delivery Prediction Input (RMSE 7.58)"""
    freight_value: float
    price: float
    product_weight_g: float
    product_description_lenght: float
    distance_km: float = 500.0  # Default if not provided
    same_state: int = 0
    seller_avg_rating: float = 4.0
    product_photos_qty: int = 2
    product_volume: float = 5000.0
    freight_ratio: float = 0.2

class ChurnInput(BaseModel):
    days_since_last_order: float
    frequency: float
    monetary: float

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
    
    try:
        # Prepare DataFrame with correct Feature Names and ORDER (LOWERCASE based on error)
        df = pd.DataFrame([{
            "recency": data.days_since_last_order,
            "frequency": data.frequency,
            "monetary": data.monetary
        }])
        
        # Ensure column order matches training (recency, frequency, monetary)
        df = df[['recency', 'frequency', 'monetary']]
        
        # Predict Class (1 = Risk)
        prediction = models["churn"].predict(df)[0]
        prob = models["churn"].predict_proba(df)[0][1]
        
        return {
            "is_churn_risk": bool(prediction),
            "churn_probability": float(prob),
            "risk_level": "Critical" if prob > 0.7 else "Medium" if prob > 0.4 else "Low"
        }
    except Exception as e:
        print(f"⚠️ Churn Prediction Error: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction Error: {str(e)}")

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



@app.post("/recommend")
def recommend_products(data: RecommendationInput, db: Session = Depends(get_db)):
    """
    Personalized Product Recommendation using SVD (Collaborative Filtering).
    Falls back to popularity-based recommendation if user is unknown.
    """
    recommendations = []
    method = "popularity_fallback (User Unknown)"
    
    # 1. Try SVD Model
    if "recommender" in models:
        try:
            artifact = models["recommender"]
            user_map = artifact.get("user_map", {})
            reverse_product_map = artifact.get("reverse_product_map", {})
            matrix_reduced = artifact.get("matrix_reduced")
            product_components = artifact.get("product_components")
            
            if data.customer_id in user_map:
                # Get User Vector
                user_idx = user_map[data.customer_id]
                user_vector = matrix_reduced[user_idx]
                
                # Compute Scores
                scores = user_vector @ product_components
                
                # Get Top Indices
                top_indices = scores.argsort()[::-1][:data.top_k].tolist()
                recommended_ids = [reverse_product_map.get(int(i), "Unknown Product") for i in top_indices]
                
                # Fetch legible names (categories) from DB for better UX
                if recommended_ids:
                    query = text("SELECT product_id, product_category_name FROM products WHERE product_id IN :ids")
                    result = db.execute(query, {"ids": tuple(recommended_ids)}).fetchall()
                    name_map = {row[0]: row[1] for row in result}
                    # Return categories (fallback to ID if category is None)
                    recommendations = [name_map.get(pid, "Unknown Product") for pid in recommended_ids]
                
                method = "personalized_svd"
        except Exception as e:
            print(f"⚠️ SVD Error: {e}")
            # Fallback to popularity
            pass
            
    # 2. Popularity Fallback (if SVD failed or user unknown)
    if not recommendations:
        # Get top selling products from DB
        try:
            query = text("""
                SELECT p.product_category_name 
                FROM order_items oi
                JOIN products p ON oi.product_id = p.product_id
                GROUP BY p.product_category_name
                ORDER BY COUNT(*) DESC
                LIMIT :limit
            """)
            result = db.execute(query, {"limit": data.top_k}).fetchall()
            recommendations = [row[0] for row in result if row[0]]
            
            # If still empty (e.g. empty DB), use generic fallback
            if not recommendations:
                recommendations = ["relogios_presentes", "cama_mesa_banho", "esporte_lazer", "informatica_acessorios", "moveis_decoracao"]
                
        except Exception as e:
            print(f"⚠️ DB Error: {e}")
            recommendations = ["relogios_presentes", "cama_mesa_banho", "esporte_lazer"]
    
    return {
        "customer_id": data.customer_id,
        "recommendations": recommendations,
        "method": method
    }
