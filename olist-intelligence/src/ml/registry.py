"""MLflow Model Registry utilities for model versioning."""
import mlflow
from mlflow.tracking import MlflowClient
from pathlib import Path
import pickle
import os
from src.config import MODELS_PATH


def get_mlflow_client():
    """Get MLflow client with proper tracking URI."""
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    mlflow.set_tracking_uri(tracking_uri)
    return MlflowClient()


def register_model(model, model_name: str, metrics: dict, params: dict = None, flavor: str = "sklearn"):
    """
    Register a model with MLflow Model Registry.
    
    Args:
        model: Trained model object
        model_name: Name for registry (e.g., 'logistics', 'churn')
        metrics: Dict of metrics (e.g., {'rmse': 7.6, 'r2': 0.85})
        params: Dict of hyperparameters
        flavor: Model flavor ('sklearn', 'catboost', 'pickle')
    
    Returns:
        model_version: Version number of registered model
    """
    try:
        with mlflow.start_run(run_name=f"{model_name}_training"):
            # Log parameters
            if params:
                mlflow.log_params(params)
            
            # Log metrics
            mlflow.log_metrics(metrics)
            
            # Log model based on flavor
            artifact_path = "model"
            if flavor == "catboost":
                mlflow.catboost.log_model(model, artifact_path=artifact_path, registered_model_name=f"olist-{model_name}")
            elif flavor == "sklearn":
                mlflow.sklearn.log_model(model, artifact_path=artifact_path, registered_model_name=f"olist-{model_name}")
            else:
                # Fallback to generic pyfunc (pickle) or just artifact
                # For dictionaries (Recommender), we just warn and skip registry for now
                if isinstance(model, dict):
                    print(f"⚠️ Dictionary artifact (Recommender) logging not fully supported in Registry yet.")
                    # We can save it as artifact but not register as Model Version easily without PyFunc wrapper
                    # For now, we rely on local save for Recommender
                    return None

            run_id = mlflow.active_run().info.run_id
        
        # Get latest version
        client = get_mlflow_client()
        versions = client.search_model_versions(f"name='olist-{model_name}'")
        latest_version = max([int(v.version) for v in versions]) if versions else 1
        
        print(f"Model registered: olist-{model_name} v{latest_version}")
        return latest_version
        
    except Exception as e:
        print(f"MLflow registration failed: {e}")
        # Fallback: save locally
        save_model_locally(model, model_name)
        return None


def save_model_locally(model, model_name: str):
    """Save model to local path as fallback."""
    path = MODELS_PATH / f"{model_name}_model.pkl"
    with open(path, 'wb') as f:
        pickle.dump(model, f)
    print(f"Model saved locally: {path}")


def load_production_model(model_name: str, flavor: str = "sklearn"):
    """
    Load production model from MLflow or local fallback.
    
    Args:
        model_name: Name of model ('logistics', 'churn', 'recommender')
        flavor: 'sklearn', 'catboost'
    
    Returns:
        Loaded model object
    """
    try:
        client = get_mlflow_client()
        model_uri = f"models:/olist-{model_name}/Production"
        
        if flavor == "catboost":
            model = mlflow.catboost.load_model(model_uri)
        else:
            model = mlflow.sklearn.load_model(model_uri)
            
        print(f"Loaded from MLflow: olist-{model_name} (Production)")
        return model
    except Exception as e:
        print(f"MLflow load failed ({e}), checking local...")
        # Fallback: load from local
        path = MODELS_PATH / f"{model_name}_model.pkl"
        if path.exists():
            with open(path, 'rb') as f:
                model = pickle.load(f)
            print(f"Loaded from local: {path}")
            return model
        raise FileNotFoundError(f"Model not found: {model_name}")


def promote_to_production(model_name: str, version: int):
    """Promote a model version to Production stage."""
    try:
        client = get_mlflow_client()
        client.transition_model_version_stage(
            name=f"olist-{model_name}",
            version=version,
            stage="Production",
            archive_existing_versions=True
        )
        print(f"Promoted olist-{model_name} v{version} to Production")
        return True
    except Exception as e:
        print(f"Promotion failed: {e}")
        return False
