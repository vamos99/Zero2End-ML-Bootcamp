import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from src.config import DATABASE_URL
from src.ml.recommender import recommend_from_artifact

# Required for local debugging if running this module directly.
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

logger = logging.getLogger(__name__)

API_KEY = os.getenv("API_KEY")
api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)
REPEAT_PURCHASE_RISK_TYPE = "repeat_purchase_risk"
REPEAT_PURCHASE_RISK_CLAIM_BOUNDARY = (
    "Offline repeat-purchase risk candidate; not measured churn reduction "
    "or retention uplift."
)

async def verify_api_key(api_key: str = Security(api_key_header)):
    """Verify API key for protected endpoints."""
    if not API_KEY:
        raise HTTPException(status_code=503, detail="API key is not configured")
    if api_key is None or api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")
    return api_key

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


def table_exists(table_name: str) -> bool:
    """Return whether a runtime table exists without querying its contents."""
    return table_name in set(inspect(engine).get_table_names())


def require_table(table_name: str):
    """Return a controlled service-unavailable response for optional outputs."""
    if not table_exists(table_name):
        raise HTTPException(
            status_code=503,
            detail=f"Required generated table is not available: {table_name}",
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load Models on Startup
    try:
        from src.ml.registry import load_production_model
        
        # Load Logistics (CatBoost)
        try:
            models["logistics"] = load_production_model("logistics", flavor="catboost")
        except Exception as e:
            logger.warning("Failed to load logistics model: %s", e)

        # Load Churn (CatBoost)
        try:
            models["churn"] = load_production_model("churn", flavor="catboost")
        except Exception as e:
            logger.warning("Failed to load churn model: %s", e)

        # Load Recommender (Dict - Local Fallback usually)
        try:
            # Recommender is not fully in Registry yet, uses local fallback path in registry
            models["recommender"] = load_production_model("recommender", flavor="sklearn")
        except Exception as e:
            logger.warning("Failed to load recommender model: %s", e)
            
        logger.info("Model loading completed. loaded_models=%s", sorted(models))
    except Exception as e:
        logger.exception("Failed to initialize model registry: %s", e)
    yield
    models.clear()

# FastAPI App
app = FastAPI(
    title="Olist Intelligence API",
    description="API for logistics predictions, repeat-purchase risk, and recommendations.",
    version="2.0.0",
    lifespan=lifespan
)

class DeliveryInput(BaseModel):
    """Ten-feature delivery prediction input."""
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


def _repeat_purchase_model_missing_response():
    raise HTTPException(
        status_code=503,
        detail={
            "message": "Repeat-purchase risk model is not loaded.",
            "prediction_type": REPEAT_PURCHASE_RISK_TYPE,
            "model_available": False,
            "claim_boundary": REPEAT_PURCHASE_RISK_CLAIM_BOUNDARY,
        },
    )


def _risk_level(probability: float) -> str:
    if probability > 0.7:
        return "Critical"
    if probability > 0.4:
        return "Medium"
    return "Low"


def _predict_repeat_purchase_risk(data: ChurnInput, include_legacy_fields: bool = False):
    if "churn" not in models:
        _repeat_purchase_model_missing_response()

    try:
        df = pd.DataFrame([{
            "recency": data.days_since_last_order,
            "frequency": data.frequency,
            "monetary": data.monetary,
        }])
        df = df[["recency", "frequency", "monetary"]]

        prediction = models["churn"].predict(df)[0]
        probability = float(models["churn"].predict_proba(df)[0][1])

        response = {
            "prediction_type": REPEAT_PURCHASE_RISK_TYPE,
            "model_available": True,
            "repeat_purchase_risk": bool(prediction),
            "repeat_purchase_risk_probability": probability,
            "risk_level": _risk_level(probability),
            "claim_boundary": REPEAT_PURCHASE_RISK_CLAIM_BOUNDARY,
        }
        if include_legacy_fields:
            response.update({
                "is_churn_risk": bool(prediction),
                "churn_probability": probability,
                "legacy_endpoint": True,
            })
        return response
    except Exception as e:
        logger.exception("Repeat-purchase risk prediction failed: %s", e)
        raise HTTPException(status_code=500, detail="Prediction Error")

@app.post("/predict/delivery")
def predict_delivery(data: DeliveryInput, _api_key: str = Depends(verify_api_key)):
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

@app.post("/predict/repeat-purchase-risk")
def predict_repeat_purchase_risk(data: ChurnInput, _api_key: str = Depends(verify_api_key)):
    """
    Repeat-purchase risk candidate prediction.
    """
    return _predict_repeat_purchase_risk(data)


@app.post("/predict/churn")
def predict_churn(data: ChurnInput, _api_key: str = Depends(verify_api_key)):
    """
    Legacy alias for repeat-purchase risk prediction.
    """
    return _predict_repeat_purchase_risk(data, include_legacy_fields=True)

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

class RecommendationInput(BaseModel):
    customer_id: str
    top_k: int = Field(default=5, ge=1, le=20)

@app.get("/")
def read_root():
    return {"message": "Welcome to Olist Intelligence API "}

@app.get("/health")
def health_check():
    """Return a lightweight liveness snapshot."""
    return {
        "status": "ok",
        "database_configured": bool(DATABASE_URL),
        "api_key_configured": bool(API_KEY),
        "loaded_models": sorted(models),
    }


@app.get("/ready")
def readiness_check():
    """Report optional generated outputs separately from API liveness."""
    generated_tables = {
        "logistics_predictions": table_exists("logistics_predictions"),
        "customer_segments": table_exists("customer_segments"),
    }
    return {
        "status": "ready" if all(generated_tables.values()) else "partial",
        "database_configured": bool(DATABASE_URL),
        "api_key_configured": bool(API_KEY),
        "generated_tables": generated_tables,
        "loaded_models": sorted(models),
    }


@app.get("/orders/{order_id}/prediction", response_model=LogisticsPrediction)
def get_order_prediction(order_id: str, db: Session = Depends(get_db)):
    """
    Get logistics prediction for a specific order.
    """
    require_table("logistics_predictions")
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
    require_table("customer_segments")
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

@app.get("/segments")
def get_segment_distribution(db: Session = Depends(get_db)):
    """Return customer counts by segment for dashboard summary cards."""
    require_table("customer_segments")
    query = text("""
        SELECT "Segment", COUNT(*) AS customer_count
        FROM customer_segments
        GROUP BY "Segment"
        ORDER BY customer_count DESC
    """)
    rows = db.execute(query, {}).fetchall()
    segments = [
        {"segment": row[0], "customer_count": int(row[1])}
        for row in rows
    ]

    return {
        "segments": segments,
        "total_customers": sum(item["customer_count"] for item in segments),
    }

@app.post("/recommend")
def recommend_products(
    data: RecommendationInput,
    db: Session = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
):
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
            final_recommendations = recommend_from_artifact(
                artifact,
                data.customer_id,
                top_k=data.top_k,
            )
            if final_recommendations:
                return {
                    "method": "personalized_svd",
                    "item_type": "product_id",
                    "recommendations": final_recommendations
                }
        except Exception as e:
            logger.warning("SVD recommendation failed; using popularity fallback: %s", e)
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
            logger.warning("Popularity recommendation query failed; using static fallback: %s", e)
            recommendations = ["relogios_presentes", "cama_mesa_banho", "esporte_lazer"]
    
    return {
        "customer_id": data.customer_id,
        "recommendations": recommendations,
        "method": method,
        "item_type": "product_category",
    }
