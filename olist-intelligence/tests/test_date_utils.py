import pandas as pd

from src.database.date_utils import filter_by_date_range


def test_filter_by_date_range_keeps_rows_inside_bounds():
    df = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-15", "2024-02-01"],
            "value": [1, 2, 3],
        }
    )

    result = filter_by_date_range(df, "date", "2024-01-10", "2024-01-31")

    assert result["value"].tolist() == [2]


def test_filter_by_date_range_returns_input_when_bounds_missing():
    df = pd.DataFrame({"date": ["2024-01-01"], "value": [1]})

    result = filter_by_date_range(df, "date")

    assert result.equals(df)
