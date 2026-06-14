from src.database.metric_names import REVENUE, RETENTION_RATE
from src.database.query_limits import clamp_limit
from src.database.table_names import ORDERS_TABLE, PRODUCTS_TABLE


def test_clamp_limit_handles_invalid_values():
    assert clamp_limit(None) == 10
    assert clamp_limit("bad") == 10
    assert clamp_limit(0) == 10


def test_clamp_limit_caps_large_values():
    assert clamp_limit(500) == 100
    assert clamp_limit(15) == 15


def test_query_contract_constants_are_defined():
    assert ORDERS_TABLE == "orders"
    assert PRODUCTS_TABLE == "products"
    assert REVENUE == "total_revenue"
    assert RETENTION_RATE == "retention_rate"
