"""Tests for feature engineering functions."""
import pytest
import numpy as np
import pandas as pd
from src.ml.features import haversine_distance, review_score_to_sentiment


class TestHaversineDistance:
    """Test Haversine distance calculation."""
    
    def test_same_location_returns_zero(self):
        """Same location should return 0 km."""
        result = haversine_distance(0, 0, 0, 0)
        assert result == 0
    
    def test_known_distance(self):
        """Test with known cities: São Paulo to Rio de Janeiro ~360km."""
        sp_lat, sp_lon = -23.5505, -46.6333
        rj_lat, rj_lon = -22.9068, -43.1729
        result = haversine_distance(sp_lat, sp_lon, rj_lat, rj_lon)
        assert 350 < result < 380  # ~360 km
    
    def test_vectorized_operation(self):
        """Test with numpy arrays."""
        lats1 = np.array([-23.5505, -22.9068])
        lons1 = np.array([-46.6333, -43.1729])
        lats2 = np.array([-22.9068, -23.5505])
        lons2 = np.array([-43.1729, -46.6333])
        result = haversine_distance(lats1, lons1, lats2, lons2)
        assert len(result) == 2
        assert result[0] == result[1]  # Same distance both ways


class TestReviewSentiment:
    """Test review score to sentiment conversion."""
    
    def test_negative_scores(self):
        """Scores 1-2 should be negative."""
        assert review_score_to_sentiment(1) == -1
        assert review_score_to_sentiment(2) == -1
    
    def test_neutral_score(self):
        """Score 3 should be neutral."""
        assert review_score_to_sentiment(3) == 0
    
    def test_positive_scores(self):
        """Scores 4-5 should be positive."""
        assert review_score_to_sentiment(4) == 1
        assert review_score_to_sentiment(5) == 1
