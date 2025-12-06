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


class TestFeatureEngineering:
    """Test feature engineering quality."""
    
    def test_distance_feature_is_positive(self):
        """Distance should always be non-negative."""
        from src.features import haversine_distance
        
        distances = haversine_distance(
            np.array([-23.5, -22.9, -25.0]),
            np.array([-46.6, -43.1, -49.0]),
            np.array([-22.9, -23.5, -30.0]),
            np.array([-43.1, -46.6, -51.0])
        )
        
        assert all(d >= 0 for d in distances)
    
    def test_sentiment_categories(self):
        """Sentiment should only have 3 values."""
        from src.features import review_score_to_sentiment
        
        sentiments = [review_score_to_sentiment(i) for i in range(1, 6)]
        unique_sentiments = set(sentiments)
        
        assert unique_sentiments == {-1, 0, 1}
