"""Tests for model training and benchmarking."""
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np


class TestBenchmarkModels:
    """Test model benchmarking utilities."""
    
    def test_model_rmse_threshold(self):
        """Model RMSE should be below acceptable threshold."""
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.model_selection import cross_val_score
        
        # Create sample data
        np.random.seed(42)
        X = np.random.rand(100, 5)
        y = np.random.rand(100) * 20  # 0-20 days
        
        model = RandomForestRegressor(n_estimators=10, random_state=42)
        scores = cross_val_score(model, X, y, cv=3, scoring='neg_root_mean_squared_error')
        rmse = -scores.mean()
        
        # RMSE should be reasonable (< 10 days for this synthetic data)
        assert rmse < 15
    
    def test_classifier_auc_threshold(self):
        """Classifier AUC should be above random (0.5)."""
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import cross_val_score
        
        # Create sample data
        np.random.seed(42)
        X = np.random.rand(100, 5)
        y = (X[:, 0] > 0.5).astype(int)  # Simple rule
        
        model = LogisticRegression(random_state=42)
        scores = cross_val_score(model, X, y, cv=3, scoring='roc_auc')
        auc = scores.mean()
        
        # AUC should be better than random
        assert auc > 0.5

    def test_benchmark_helpers_calculate_improvement_and_control_artifact_writes(self, tmp_path):
        """Benchmark helpers should not write model artifacts unless explicitly requested."""
        from src.ml import benchmark

        model_path = tmp_path / "models" / "example.pkl"

        assert benchmark._improvement_pct(10.0, 7.5) == 25.0
        assert not benchmark._maybe_save_pickle({"model": "demo"}, model_path, save_artifacts=False)
        assert not model_path.exists()

        assert benchmark._maybe_save_pickle({"model": "demo"}, model_path, save_artifacts=True)
        assert model_path.exists()

    def test_logistics_benchmark_defaults_to_measurement_only(self, tmp_path, monkeypatch):
        """Logistics benchmark should report baselines without creating local artifacts by default."""
        from src.ml import benchmark

        class MeanRegressor:
            def fit(self, _x, y):
                self.mean_ = float(np.mean(y))
                return self

            def predict(self, x):
                return np.full(len(x), self.mean_)

        features = pd.DataFrame(
            {
                "freight_value": [10, 20, 30, 40, 50, 60],
                "price": [100, 110, 120, 130, 140, 150],
            }
        )
        target = pd.Series([5, 6, 7, 8, 9, 10], name="actual_days")
        timestamps = pd.Series(pd.date_range("2018-01-01", periods=6, freq="D"))
        estimates = pd.Series([6, 6, 8, 8, 11, 11], name="estimated_days")

        monkeypatch.setattr(benchmark, "MODELS_PATH", tmp_path / "models")
        monkeypatch.setattr(
            benchmark,
            "get_logistics_data",
            lambda **_kwargs: (features, target, timestamps, estimates),
        )
        monkeypatch.setattr(benchmark, "LinearRegression", MeanRegressor)
        monkeypatch.setattr(benchmark, "RandomForestRegressor", lambda **_kwargs: MeanRegressor())
        monkeypatch.setattr(benchmark, "CatBoostRegressor", lambda **_kwargs: MeanRegressor())
        monkeypatch.setattr(benchmark, "expanding_temporal_splits", lambda *_args, **_kwargs: [])

        result = benchmark.benchmark_logistics(limit=6, optimize=False)

        assert "baselines" in result
        assert "train_mean_mae" in result["baselines"]
        assert "source_estimate_mae" in result["baselines"]
        assert not (tmp_path / "models" / "logistics_model.pkl").exists()

    def test_late_delivery_classification_reports_decision_metrics(self, tmp_path, monkeypatch):
        """Late-delivery benchmark should use classification metrics, not accuracy-only reporting."""
        from src.ml import benchmark

        class ProbabilityClassifier:
            def fit(self, _x, _y):
                return self

            def predict_proba(self, x):
                proba = np.asarray(x["freight_value"], dtype=float)
                proba = proba / proba.max()
                return np.column_stack([1 - proba, proba])

            def predict(self, x):
                return (self.predict_proba(x)[:, 1] >= 0.5).astype(int)

        features = pd.DataFrame(
            {
                "freight_value": [1, 2, 8, 9, 1, 2, 8, 9, 1, 2],
                "price": [10] * 10,
            }
        )
        actual_days = pd.Series([3, 3, 8, 9, 3, 3, 8, 9, 3, 8], name="actual_days")
        estimated_days = pd.Series([5, 5, 5, 5, 5, 5, 5, 5, 5, 5], name="estimated_days")
        timestamps = pd.Series(pd.date_range("2018-01-01", periods=10, freq="D"))

        monkeypatch.setattr(benchmark, "MODELS_PATH", tmp_path / "models")
        monkeypatch.setattr(
            benchmark,
            "get_logistics_data",
            lambda **_kwargs: (features, actual_days, timestamps, estimated_days),
        )
        monkeypatch.setattr(benchmark, "LogisticRegression", lambda **_kwargs: ProbabilityClassifier())
        monkeypatch.setattr(benchmark, "RandomForestClassifier", lambda **_kwargs: ProbabilityClassifier())
        monkeypatch.setattr(benchmark, "CatBoostClassifier", lambda **_kwargs: ProbabilityClassifier())

        result = benchmark.benchmark_late_delivery_classification(limit=10)

        assert result["target"] == "order_delivered_customer_date > order_estimated_delivery_date"
        assert result["split"] == "time_based_holdout"
        assert "accuracy" not in result["LogisticRegression"]
        assert {"roc_auc", "pr_auc", "precision", "recall", "f1", "confusion_matrix"} <= set(
            result["LogisticRegression"]
        )
        assert not (tmp_path / "models" / "late_delivery_classifier.pkl").exists()


class TestFeatureEngineering:
    """Test feature engineering quality."""
    
    def test_distance_feature_is_positive(self):
        """Distance should always be non-negative."""
        from src.ml.features import haversine_distance
        
        distances = haversine_distance(
            np.array([-23.5, -22.9, -25.0]),
            np.array([-46.6, -43.1, -49.0]),
            np.array([-22.9, -23.5, -30.0]),
            np.array([-43.1, -46.6, -51.0])
        )
        
        assert all(d >= 0 for d in distances)
    
    def test_sentiment_categories(self):
        """Sentiment should only have 3 values."""
        from src.ml.features import review_score_to_sentiment
        
        sentiments = [review_score_to_sentiment(i) for i in range(1, 6)]
        unique_sentiments = set(sentiments)
        
        assert unique_sentiments == {-1, 0, 1}
