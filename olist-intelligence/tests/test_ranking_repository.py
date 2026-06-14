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
            "order_id": ["o1", "o2", "o3"],
            "price": [20.0, 40.0, 100.0],
            "order_purchase_timestamp": ["2024-01-01", "2024-02-01", "2025-01-01"],
        }
    )

    with patch("src.database.ranking_repository.pd.read_sql", return_value=source):
        result = ranking_repository.get_top_products(
            limit=500,
            start_date="2024-01-01",
            end_date="2024-12-31",
        )

    assert result.to_dict("records") == [
        {"product_category": "books", "order_count": 2, "total_sales": 60.0}
    ]


def test_top_sellers_returns_stable_fallback_on_query_error():
    with patch(
        "src.database.ranking_repository.pd.read_sql",
        side_effect=RuntimeError("db unavailable"),
    ):
        result = ranking_repository.get_top_sellers(limit="invalid")

    assert result.empty
    assert result.columns.tolist() == TOP_SELLER_COLUMNS


def test_ranking_empty_contracts_match_dashboard_outputs():
    with patch("src.database.ranking_repository.pd.read_sql", return_value=pd.DataFrame()):
        products = ranking_repository.get_top_products()
        categories = ranking_repository.get_category_performance()

    assert products.columns.tolist() == TOP_PRODUCT_COLUMNS
    assert categories.columns.tolist() == CATEGORY_PERFORMANCE_COLUMNS
