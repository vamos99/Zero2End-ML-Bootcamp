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
        
        # Create 5 orders for s1 to pass the >=5 order filter
        mock_df = pd.DataFrame({
            'seller_id': ['s1'] * 6,
            'price': [100.0] * 6,
            'review_score': [5] * 6,
            'order_id': [f'o{i}' for i in range(6)],
            'order_delivered_customer_date': [pd.Timestamp('2024-01-05')] * 6,
            'order_estimated_delivery_date': [pd.Timestamp('2024-01-10')] * 6,
            'order_purchase_timestamp': [pd.Timestamp('2024-01-01')] * 6
        })
        
        with patch('pandas.read_sql', return_value=mock_df):
            result = get_top_sellers(10)
            assert not result.empty

    @patch('src.database.repository.engine')
    def test_get_revenue_metrics(self, mock_engine):
        """Test executive revenue metric calculation."""
        from src.database.repository import get_revenue_metrics

        mock_df = pd.DataFrame({
            'order_id': ['o1', 'o2'],
            'customer_id': ['c1', 'c1'],
            'product_revenue': [100.0, 50.0],
            'freight_revenue': [10.0, 5.0],
        })

        with patch('pandas.read_sql', return_value=mock_df):
            result = get_revenue_metrics('2024-01-01', '2024-01-31')

            assert result['total_revenue'] == 150.0
            assert result['avg_order_value'] == 75.0
            assert result['unique_customers'] == 1

    @patch('src.database.repository.engine')
    def test_get_review_delivery_quality(self, mock_engine):
        """Test delivery and review quality metric calculation."""
        from src.database.repository import get_review_delivery_quality

        mock_df = pd.DataFrame({
            'order_id': ['o1', 'o2'],
            'order_delivered_customer_date': ['2024-01-05', '2024-01-15'],
            'order_estimated_delivery_date': ['2024-01-07', '2024-01-10'],
            'review_score': [5, 2],
            'is_late': [0, 1],
        })

        with patch('pandas.read_sql', return_value=mock_df):
            result = get_review_delivery_quality('2024-01-01', '2024-01-31')

            assert result['avg_review_score'] == 3.5
            assert result['late_delivery_rate'] == 50.0
            assert result['review_count'] == 2

    @patch('src.database.repository.engine')
    def test_get_payment_mix_summary(self, mock_engine):
        """Test payment mix mart retrieval."""
        from src.database.repository import get_payment_mix_summary

        mock_df = pd.DataFrame({
            'payment_type': ['credit_card'],
            'orders': [10],
            'payment_records': [12],
            'payment_value': [1000.0],
            'avg_installments': [2.5],
        })

        with patch('pandas.read_sql', return_value=mock_df):
            result = get_payment_mix_summary('2024-01-01', '2024-01-31')

            assert result.iloc[0]['payment_type'] == 'credit_card'
            assert result.iloc[0]['payment_value'] == 1000.0

    @patch('src.database.repository.engine')
    def test_get_cohort_retention_matrix(self, mock_engine):
        """Test cohort retention mart retrieval."""
        from src.database.repository import get_cohort_retention_matrix

        mock_df = pd.DataFrame({
            'cohort_month': ['2024-01', '2024-01'],
            'months_since_first_order': [0, 1],
            'cohort_customers': [100, 100],
            'active_customers': [100, 12],
            'retention_rate': [100.0, 12.0],
        })

        with patch('pandas.read_sql', return_value=mock_df):
            result = get_cohort_retention_matrix('2024-01-01', '2024-03-31')

            assert list(result['months_since_first_order']) == [0, 1]
            assert result.iloc[1]['retention_rate'] == 12.0

    @patch('src.database.repository.engine')
    def test_get_seller_sla_watchlist(self, mock_engine):
        """Test seller SLA watchlist mart retrieval."""
        from src.database.repository import get_seller_sla_watchlist

        mock_df = pd.DataFrame({
            'seller_id': ['s1'],
            'seller_state': ['SP'],
            'orders': [25],
            'product_revenue': [5000.0],
            'avg_review_score': [3.8],
            'avg_delivery_days': [11.2],
            'late_delivery_rate': [42.0],
        })

        with patch('pandas.read_sql', return_value=mock_df):
            result = get_seller_sla_watchlist()

            assert result.iloc[0]['seller_id'] == 's1'
            assert result.iloc[0]['late_delivery_rate'] == 42.0
