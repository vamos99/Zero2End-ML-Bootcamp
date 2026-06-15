from unittest.mock import MagicMock, patch

import pandas as pd

from src.ml.data import get_churn_data, get_logistics_data


def test_logistics_data_binds_limit_and_returns_sorted_timestamps():
    rows = pd.DataFrame(
        {
            "order_purchase_timestamp": ["2018-02-01", "2018-01-01"],
            "order_delivered_customer_date": ["2018-02-04", "2018-01-03"],
            "freight_value": [20.0, 10.0],
            "price": [100.0, 50.0],
            "product_weight_g": [500.0, 250.0],
            "product_description_lenght": [100.0, 50.0],
            "product_photos_qty": [2, 1],
            "product_volume": [1_000.0, 500.0],
            "seller_lat": [-23.5, -22.9],
            "seller_lng": [-46.6, -43.2],
            "cust_lat": [-23.6, -22.8],
            "cust_lng": [-46.7, -43.1],
            "same_state": [1, 1],
            "seller_avg_rating": [4.5, 4.0],
        }
    )
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = MagicMock()

    with (
        patch("src.ml.data.get_db_engine", return_value=engine),
        patch("src.ml.data.pd.read_sql", return_value=rows) as read_sql,
    ):
        features, target, timestamps = get_logistics_data(limit=5, include_timestamps=True)

    assert read_sql.call_args.kwargs["params"] == {"limit": 5}
    assert timestamps.tolist() == sorted(timestamps.tolist())
    assert target.tolist() == [2.0, 3.0]
    assert features.columns.tolist() == [
        "freight_value",
        "price",
        "product_weight_g",
        "product_description_lenght",
        "distance_km",
        "same_state",
        "seller_avg_rating",
        "product_photos_qty",
        "product_volume",
        "freight_ratio",
    ]


def test_churn_features_precede_future_label_window():
    orders = pd.DataFrame(
        {
            "customer_unique_id": ["active", "active", "churned"],
            "order_purchase_timestamp": [
                "2018-01-01",
                "2018-05-15",
                "2018-02-01",
            ],
            "order_id": ["o1", "o2", "o3"],
            "price": [100.0, 50.0, 80.0],
        }
    )
    max_date = pd.DataFrame([["2018-06-01"]])

    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = MagicMock()

    with (
        patch("src.ml.data.get_db_engine", return_value=engine),
        patch("src.ml.data.pd.read_sql", side_effect=[orders, max_date]),
    ):
        features, target = get_churn_data()

    result = features.assign(churned=target).sort_values("recency")

    assert "churned" not in features.columns
    assert result["recency"].tolist() == [30, 61]
    assert result["churned"].tolist() == [1, 0]
