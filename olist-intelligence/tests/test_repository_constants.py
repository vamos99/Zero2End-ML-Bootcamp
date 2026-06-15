from src.database.repository_columns import (
    COHORT_RETENTION_COLUMNS,
    LOGISTICS_DETAILS_COLUMNS,
    PAYMENT_MIX_COLUMNS,
    REVENUE_BY_STATE_COLUMNS,
    REVIEW_DELIVERY_MATRIX_COLUMNS,
    SELLER_SLA_COLUMNS,
    TARGET_AUDIENCE_COLUMNS,
)
from src.database.repository_defaults import EMPTY_REVIEW_DELIVERY, EMPTY_TOTALS


def test_repository_defaults_are_numeric_contracts():
    assert EMPTY_TOTALS["total_revenue"] == 0.0
    assert EMPTY_REVIEW_DELIVERY["review_count"] == 0


def test_repository_column_contracts_are_defined():
    assert "payment_value" in PAYMENT_MIX_COLUMNS
    assert "retention_rate" in COHORT_RETENTION_COLUMNS
    assert REVENUE_BY_STATE_COLUMNS == ["customer_state", "order_count", "revenue"]
    assert REVIEW_DELIVERY_MATRIX_COLUMNS[-1] == "late_delivery_rate"
    assert SELLER_SLA_COLUMNS[0] == "seller_id"
    assert LOGISTICS_DETAILS_COLUMNS[-1] == "order_purchase_timestamp"
    assert TARGET_AUDIENCE_COLUMNS[0] == "customer_unique_id"
