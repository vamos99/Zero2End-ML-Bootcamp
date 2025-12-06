"""Tests for database repository functions."""
import pytest
from unittest.mock import patch
import pandas as pd


class TestRepository:
    """Test database repository functions."""
    
    @patch('src.database.repository.engine')
    def test_get_total_orders(self, mock_engine):
        """Test total orders retrieval."""
        from src.database.repository import get_total_orders
        
        mock_df = pd.DataFrame([[100]])
        with patch('pandas.read_sql', return_value=mock_df):
            result = get_total_orders('2024-01-01', '2024-01-31')
            assert result == 100
    
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
