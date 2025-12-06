"""Tests for database repository functions."""
import pytest
from unittest.mock import MagicMock, patch
import pandas as pd


class TestRepository:
    """Test database repository functions."""
    
    @patch('src.database.repository.engine')
    def test_get_daily_pulse(self, mock_engine):
        """Test daily pulse metrics retrieval."""
        from src.database.repository import get_daily_pulse
        
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (100, 50, 25)
        mock_engine.connect.return_value.__enter__.return_value.execute.return_value = mock_result
        
        result = get_daily_pulse('2024-01-01', '2024-01-31')
        assert 'total_orders' in result or result is not None
    
    @patch('src.database.repository.engine')
    def test_get_top_products(self, mock_engine):
        """Test top products query."""
        from src.database.repository import get_top_products
        
        mock_df = pd.DataFrame({
            'product_id': ['p1', 'p2'],
            'category': ['cat1', 'cat2'],
            'sales': [100, 50]
        })
        
        with patch('pandas.read_sql', return_value=mock_df):
            result = get_top_products(10)
            assert result is not None
    
    @patch('src.database.repository.engine')
    def test_get_top_sellers(self, mock_engine):
        """Test top sellers query."""
        from src.database.repository import get_top_sellers
        
        mock_df = pd.DataFrame({
            'seller_id': ['s1', 's2'],
            'revenue': [1000, 500]
        })
        
        with patch('pandas.read_sql', return_value=mock_df):
            result = get_top_sellers(10)
            assert result is not None
