from unittest.mock import patch

import pandas as pd

from src.database import ranking_repository
from src.database.ranking_schema import (
    CATEGORY_PERFORMANCE_COLUMNS,
    TOP_PRODUCT_COLUMNS,
    TOP_SELLER_COLUMNS,
)


def test_top_products_filters_window_and_clamps_limit():
    source = pd.DataFrame(
        {
            "product_category": ["books", "books", "toys"],
            "order_count": [2, 1, 1],
            "total_sales": [60.0, 100.0, 30.0],
        }
    )

    with patch("src.database.ranking_repository.pd.read_sql", return_value=source) as read_sql:
        result = ranking_repository.get_top_products(
            limit=500,
            start_date="2024-01-01",
            end_date="2024-12-31",
        )

    assert read_sql.call_args.kwargs["params"] == {
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "limit": 100,
    }
    assert result.columns.tolist() == TOP_PRODUCT_COLUMNS


def test_top_sellers_returns_stable_fallback_on_query_error():
    with patch(
        "src.database.ranking_repository.pd.read_sql",
        side_effect=RuntimeError("db unavailable"),
    ):
        result = ranking_repository.get_top_sellers(limit="invalid")

    assert result.empty
    assert result.columns.tolist() == TOP_SELLER_COLUMNS


def test_top_sellers_binds_window_and_normalized_limit():
    source = pd.DataFrame(
        {
            "seller_id": ["s1"],
            "order_count": [6],
            "total_revenue": [600.0],
            "avg_rating": [5.0],
            "on_time_count": [6],
            "total_rows": [6],
            "on_time_rate": [100.0],
        }
    )

    with patch("src.database.ranking_repository.pd.read_sql", return_value=source) as read_sql:
        result = ranking_repository.get_top_sellers(
            limit="invalid",
            start_date="2024-01-01",
            end_date="2024-12-31",
        )

    assert read_sql.call_args.kwargs["params"] == {
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "limit": 20,
    }
    assert result.to_dict("records") == source.to_dict("records")


def test_ranking_empty_contracts_match_dashboard_outputs():
    with patch("src.database.ranking_repository.pd.read_sql", return_value=pd.DataFrame()):
        products = ranking_repository.get_top_products()
        categories = ranking_repository.get_category_performance()

    assert products.columns.tolist() == TOP_PRODUCT_COLUMNS
    assert categories.columns.tolist() == CATEGORY_PERFORMANCE_COLUMNS
