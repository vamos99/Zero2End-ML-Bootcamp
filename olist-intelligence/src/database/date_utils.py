import pandas as pd


def filter_by_date_range(df, column, start_date=None, end_date=None):
    if df.empty or not start_date or not end_date:
        return df

    result = df.copy()
    result[column] = pd.to_datetime(result[column])
    return result[
        (result[column] >= pd.to_datetime(start_date))
        & (result[column] <= pd.to_datetime(end_date))
    ]
