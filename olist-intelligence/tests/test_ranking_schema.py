from src.database.ranking_schema import (
    CATEGORY_PERFORMANCE_COLUMNS,
    TOP_PRODUCT_COLUMNS,
    TOP_SELLER_COLUMNS,
)


def test_ranking_schema_columns_are_defined():
    assert "total_sales" in TOP_PRODUCT_COLUMNS
    assert "seller_id" in TOP_SELLER_COLUMNS
    assert "category" in CATEGORY_PERFORMANCE_COLUMNS
