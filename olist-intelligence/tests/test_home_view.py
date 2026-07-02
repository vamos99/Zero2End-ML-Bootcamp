import pandas as pd

from src.views.home_view import _category_signal_table, _location_lane_table, _scorecard_markdown


def test_scorecard_markdown_keeps_measured_change_visible():
    rows = [
        {
            "area": "Actual delivery operation",
            "baseline": "6.77% late rate",
            "current_or_target": "No post-intervention delivery period",
            "measured_change": "No actual delivery-time improvement measured",
            "status": "Source baseline only",
        }
    ]

    result = _scorecard_markdown(rows)

    assert "Actual delivery operation" in result
    assert "No actual delivery-time improvement measured" in result
    assert "Source baseline only" in result


def test_category_signal_table_uses_reader_friendly_columns():
    category_rows = pd.DataFrame(
        {
            "category": ["health_beauty"],
            "orders": [8647],
            "items": [9465],
            "product_revenue": [1233131.72],
            "freight_revenue": [178957.81],
            "avg_review_score": [4.23],
            "avg_delivery_days": [12.1],
            "late_delivery_rate": [7.51],
        }
    )

    result = _category_signal_table(category_rows)

    assert result.columns.tolist() == [
        "Category",
        "Orders",
        "Product revenue",
        "Avg. review",
        "Late delivery",
    ]
    assert result.iloc[0]["Category"] == "health_beauty"
    assert result.iloc[0]["Late delivery"] == 7.51


def test_location_lane_table_builds_state_lane_label():
    location_rows = pd.DataFrame(
        {
            "customer_state": ["SP"],
            "seller_state": ["RJ"],
            "lane_type": ["cross_state"],
            "orders": [120],
            "sellers": [8],
            "items": [130],
            "product_revenue": [10000.0],
            "freight_revenue": [1200.0],
            "avg_review_score": [4.0],
            "avg_delivery_days": [8.5],
            "late_delivery_rate": [12.0],
            "customer_geo_coverage_pct": [99.0],
            "seller_geo_coverage_pct": [100.0],
        }
    )

    result = _location_lane_table(location_rows)

    assert result.columns.tolist() == [
        "Lane",
        "Lane type",
        "Orders",
        "Product revenue",
        "Avg. delivery days",
        "Late delivery",
    ]
    assert result.iloc[0]["Lane"] == "RJ -> SP"
    assert result.iloc[0]["Lane type"] == "cross_state"
