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
        
        # Add required timestamp column
        mock_df = pd.DataFrame({
            'order_purchase_timestamp': ['2024-01-15', '2024-01-20']
        })
        with patch('pandas.read_sql', return_value=mock_df):
            result = get_total_orders('2024-01-01', '2024-01-31')
            assert result == 2
    
    @patch('src.database.repository.engine')
    def test_get_top_products(self, mock_engine):
        """Test top products query."""
        from src.database.repository import get_top_products
        
        mock_df = pd.DataFrame({
            'product_id': ['p1', 'p2'],
            'product_category': ['cat1', 'cat2'], # Fixed key
            'price': [100, 50],
            'order_id': ['o1', 'o2'], # needed for nunique
            'order_purchase_timestamp': ['2024-01-01', '2024-01-01'] # needed if date filter used (even if None defaulting logic checks cols)
        })
        
        with patch('pandas.read_sql', return_value=mock_df):
            result = get_top_products(10)
            assert not result.empty
    
    @patch('src.database.repository.engine')
    def test_get_top_sellers(self, mock_engine):
        """Test top sellers query."""
        from src.database.repository import get_top_sellers
        
        mock_df = pd.DataFrame({
            'seller_id': ['s1', 's2'],
            'price': [1000, 500],
            'review_score': [5, 4],
            'order_id': ['o1', 'o2'],
            'order_delivered_customer_date': ['2024-01-05', '2024-01-06'],
            'order_estimated_delivery_date': ['2024-01-10', '2024-01-10'],
            'order_purchase_timestamp': ['2024-01-01', '2024-01-01']
        })
        
        with patch('pandas.read_sql', return_value=mock_df):
            result = get_top_sellers(10)
            assert not result.empty
