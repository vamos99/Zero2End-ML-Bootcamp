import pandas as pd


def empty_frame(columns):
    return pd.DataFrame(columns=columns)


def empty_frame_from(*columns):
    return empty_frame(list(columns))
