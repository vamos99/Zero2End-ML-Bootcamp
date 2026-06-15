import numpy as np
from catboost import CatBoostRegressor, CatBoostClassifier
from sklearn.decomposition import TruncatedSVD
from scipy.sparse import csr_matrix
from sklearn.metrics import balanced_accuracy_score, mean_squared_error, roc_auc_score
from sklearn.model_selection import train_test_split
from src.config import MODELS_PATH
from src.ml.data import get_logistics_data, get_churn_data, get_recommender_data
from src.ml.evaluation import has_usable_class_balance, temporal_train_test_split
from src.ml.registry import register_model, save_model_locally

MODELS_PATH.mkdir(parents=True, exist_ok=True)

def train_logistics_model():
    """
    Logistics model using the centralized data loader and held-out evaluation.
    """
    print("📦 Eğitim Verisi Hazırlanıyor: Lojistik (10 özellik)...")
    
    X, y, timestamps = get_logistics_data(limit=50000, include_timestamps=True)
    
    print(f"📦 Model Eğitiliyor (Veri: {len(X)} satır, {X.shape[1]} özellik)...")
    model = CatBoostRegressor(iterations=200, depth=8, learning_rate=0.1, verbose=0, random_seed=42)
    X_train, X_test, y_train, y_test = temporal_train_test_split(
        X, y, timestamps, test_size=0.2
    )
    model.fit(X_train, y_train)

    pred = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, pred))
    metrics = {"rmse": rmse}
    params = {"iterations": 200, "depth": 8, "learning_rate": 0.1}
    
    model.fit(X, y)

    # Register to MLflow (fallback to local if fails)
    register_model(model, "logistics", metrics, params, flavor="catboost")
    
    # Ensure local copy for simple API usage (optional, but good for redundancy)
    save_model_locally(model, "logistics")
    
    print(f"✅ Lojistik Modeli Tamamlandı (RMSE: {rmse:.4f})")

def train_churn_model():
    print("🔥 Eğitim Verisi Hazırlanıyor: Churn...")
    
    try:
        X, y = get_churn_data(limit=50000)
    except Exception as e:
        print(f"⚠️ Veri hatası: {e}")
        return

    if not has_usable_class_balance(y):
        counts = y.value_counts().sort_index().to_dict()
        print(f"⚠️ Churn model skipped: class balance is not evaluation-ready ({counts}).")
        return

    print(f"🔥 Model Eğitiliyor (Veri: {len(X)} satır)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    model = CatBoostClassifier(
        iterations=100,
        depth=4,
        learning_rate=0.1,
        verbose=0,
        random_seed=42,
        auto_class_weights="Balanced",
    )
    model.fit(X_train, y_train)

    pred = model.predict(X_test)
    pred_proba = model.predict_proba(X_test)[:, 1]
    balanced_acc = balanced_accuracy_score(y_test, pred)
    auc = roc_auc_score(y_test, pred_proba)
    metrics = {"balanced_accuracy": balanced_acc, "roc_auc": auc}
    params = {"iterations": 100, "depth": 4}
    
    model.fit(X, y)

    # Register
    register_model(model, "churn", metrics, params, flavor="catboost")
    save_model_locally(model, "churn")
        
    print(f"✅ Churn Modeli Tamamlandı (Balanced Acc: {balanced_acc:.4f}, AUC: {auc:.4f})")

def train_recommender_model():
    print("🛍️ Eğitim Verisi Hazırlanıyor: Ürün Öneri Sistemi...")
    
    df = get_recommender_data(limit=None)
    if df.empty:
        print("⚠️ Veri bulunamadı.")
        return

    print(f"🛍️ Matris Oluşturuluyor ({len(df)} etkileşim)...")
    
    # Create User-Item Matrix
    user_ids = df['customer_id'].unique()
    product_ids = df['product_id'].unique()
    
    user_map = {id_: i for i, id_ in enumerate(user_ids)}
    product_map = {id_: i for i, id_ in enumerate(product_ids)}
    reverse_product_map = {i: id_ for id_, i in product_map.items()}
    
    df['user_idx'] = df['customer_id'].map(user_map)
    df['product_idx'] = df['product_id'].map(product_map)
    
    # SPARSE MATRIX CONSTRUCTION
    matrix_sparse = csr_matrix(
        (df['purchase_count'].values, (df['user_idx'].values, df['product_idx'].values)),
        shape=(len(user_ids), len(product_ids))
    )
    
    print(f"🛍️ Model (SVD) Eğitiliyor (Shape: {matrix_sparse.shape})...")
    
    # Reduce to 20 latent features
    svd = TruncatedSVD(n_components=min(20, len(product_ids)-1), random_state=42)
    matrix_reduced = svd.fit_transform(matrix_sparse)
    
    # We save everything needed for inference
    artifact = {
        "model": svd,
        "matrix_reduced": matrix_reduced, # User vectors
        "product_components": svd.components_, # Item vectors
        "user_map": user_map,
        "product_map": product_map,
        "reverse_product_map": reverse_product_map
    }
    
    # Currently Registry doesn't support Dict artifacts easily, so we save locally
    save_model_locally(artifact, "recommender")
    # Optional: We could log artifact to MLflow run without registering as "Model"
    # But for simplicity we keep it local for now
        
    print(f"✅ Öneri Modeli Kaydedildi (Local)")

if __name__ == "__main__":
    train_logistics_model()
    train_churn_model()
    train_recommender_model()
