import pandas as pd
from src.database.date_utils import filter_by_date_range


def test_dates():
    df = pd.DataFrame({"d": ["2024-01-01", "2024-01-15"], "v": [1, 2]})
    out = filter_by_date_range(df, "d", "2024-01-10", "2024-01-31")
    assert out["v"].tolist() == [2]
