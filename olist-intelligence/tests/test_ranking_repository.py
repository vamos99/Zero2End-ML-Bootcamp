from src.database import ranking_repository


def test_ranking_repository_has_top_products_function():
    assert callable(ranking_repository.get_top_products)
