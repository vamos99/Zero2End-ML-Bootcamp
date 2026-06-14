"""Tests for database repository functions."""
import pytest
from unittest.mock import patch
import pandas as pd
from src.database.repository_columns import (
    COHORT_RETENTION_COLUMNS,
    PAYMENT_MIX_COLUMNS,
    REVENUE_BY_STATE_COLUMNS,
    REVIEW_DELIVERY_MATRIX_COLUMNS,
)
from src.database.repository_defaults import EMPTY_REVIEW_DELIVERY, EMPTY_TOTALS


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

    def test_ranking_facade_delegates_without_breaking_legacy_imports(self):
        """Legacy repository imports delegate to the focused ranking module."""
        from src.database.repository import get_category_performance, get_top_products

        expected = pd.DataFrame({"product_category": ["books"]})
        with patch(
            "src.database.repository.ranking_repository.get_top_products",
            return_value=expected,
        ) as get_top_products_impl:
            result = get_top_products(7, "2024-01-01", "2024-01-31")

        assert result is expected
        get_top_products_impl.assert_called_once_with(7, "2024-01-01", "2024-01-31")
        assert callable(get_category_performance)

    def test_action_facade_delegates_without_breaking_service_imports(self):
        """Action service imports continue through the repository facade."""
        from src.database.repository import get_recent_actions

        expected = pd.DataFrame({"action_type": ["refresh"]})
        with patch(
            "src.database.repository.action_repository.get_recent_actions",
            return_value=expected,
        ) as get_recent_actions_impl:
            result = get_recent_actions(8)

        assert result is expected
        get_recent_actions_impl.assert_called_once_with(8)

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
    def test_get_revenue_metrics_returns_fresh_default_on_error(self, mock_engine):
        """Repository errors return a stable fallback without exposing shared state."""
        from src.database.repository import get_revenue_metrics

        with patch('pandas.read_sql', side_effect=RuntimeError('db unavailable')):
            first = get_revenue_metrics('2024-01-01', '2024-01-31')
            second = get_revenue_metrics('2024-01-01', '2024-01-31')

        assert first == EMPTY_TOTALS
        assert first is not EMPTY_TOTALS
        assert first is not second

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
    def test_get_review_delivery_quality_returns_default_for_empty_result(self, mock_engine):
        """Empty query results preserve the review-quality fallback contract."""
        from src.database.repository import get_review_delivery_quality

        with patch('pandas.read_sql', return_value=pd.DataFrame()):
            result = get_review_delivery_quality('2024-01-01', '2024-01-31')

        assert result == EMPTY_REVIEW_DELIVERY
        assert result is not EMPTY_REVIEW_DELIVERY

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

        with patch('pandas.read_sql', return_value=mock_df) as mock_read_sql:
            result = get_payment_mix_summary('2024-01-01', '2024-01-31', limit=500)

            assert result.iloc[0]['payment_type'] == 'credit_card'
            assert result.iloc[0]['payment_value'] == 1000.0
            assert mock_read_sql.call_args.kwargs['params']['limit'] == 100

    @patch('src.database.repository.engine')
    def test_get_payment_mix_summary_uses_contract_fallback_and_default_limit(self, mock_engine):
        """Invalid limits are normalized and DB errors return the shared column contract."""
        from src.database.repository import get_payment_mix_summary

        with patch('pandas.read_sql', side_effect=RuntimeError('mart unavailable')) as mock_read_sql:
            result = get_payment_mix_summary('2024-01-01', '2024-01-31', limit='invalid')

        assert result.columns.tolist() == PAYMENT_MIX_COLUMNS
        assert result.empty
        assert mock_read_sql.call_args.kwargs['params']['limit'] == 6

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
    def test_repository_rankings_normalize_limits_and_use_contract_fallbacks(self, mock_engine):
        """Ranking-style queries clamp limits and retain stable empty schemas."""
        from src.database.repository import (
            get_cohort_retention_matrix,
            get_revenue_by_state,
            get_review_delivery_matrix,
        )

        with patch('pandas.read_sql', side_effect=RuntimeError('db unavailable')) as mock_read_sql:
            revenue = get_revenue_by_state('2024-01-01', '2024-01-31', limit=500)
            review = get_review_delivery_matrix('2024-01-01', '2024-01-31')
            cohort = get_cohort_retention_matrix(
                '2024-01-01',
                '2024-03-31',
                max_cohorts='invalid',
                max_months=500,
            )

        assert revenue.columns.tolist() == REVENUE_BY_STATE_COLUMNS
        assert review.columns.tolist() == REVIEW_DELIVERY_MATRIX_COLUMNS
        assert cohort.columns.tolist() == COHORT_RETENTION_COLUMNS
        assert mock_read_sql.call_args_list[0].kwargs['params']['limit'] == 100
        assert mock_read_sql.call_args_list[2].kwargs['params']['max_cohorts'] == 8
        assert mock_read_sql.call_args_list[2].kwargs['params']['max_months'] == 100

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
