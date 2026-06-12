from src.database.ranking_schema import TOP_PRODUCT_COLUMNS, TOP_SELLER_COLUMNS


def test_ranking_schema_columns_are_defined():
    assert "total_revenue" in TOP_PRODUCT_COLUMNS
    assert "seller_id" in TOP_SELLER_COLUMNS
