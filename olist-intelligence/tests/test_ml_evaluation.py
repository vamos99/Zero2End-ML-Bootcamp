import pandas as pd
import pytest

from src.ml.evaluation import (
    expanding_temporal_splits,
    has_usable_class_balance,
    temporal_train_test_split,
)


def test_temporal_split_uses_latest_rows_for_holdout():
    features = pd.DataFrame({"value": [3, 1, 4, 2]})
    target = pd.Series([30, 10, 40, 20])
    timestamps = pd.Series(["2024-03-01", "2024-01-01", "2024-04-01", "2024-02-01"])

    X_train, X_test, y_train, y_test = temporal_train_test_split(
        features, target, timestamps, test_size=0.5
    )

    assert X_train["value"].tolist() == [1, 2]
    assert X_test["value"].tolist() == [3, 4]
    assert y_train.tolist() == [10, 20]
    assert y_test.tolist() == [30, 40]


def test_temporal_split_rejects_invalid_contract():
    with pytest.raises(ValueError):
        temporal_train_test_split(pd.DataFrame({"x": [1]}), pd.Series([1]), pd.Series(["2024-01-01"]))


def test_temporal_split_keeps_equal_timestamps_in_same_partition():
    features = pd.DataFrame({"value": [1, 2, 3, 4]})
    target = pd.Series([10, 20, 30, 40])
    timestamps = pd.Series(["2024-01-01", "2024-02-01", "2024-02-01", "2024-03-01"])

    X_train, X_test, _, _ = temporal_train_test_split(
        features, target, timestamps, test_size=0.5
    )

    assert X_train["value"].tolist() == [1]
    assert X_test["value"].tolist() == [2, 3, 4]


def test_class_balance_gate_rejects_extreme_imbalance():
    assert not has_usable_class_balance(pd.Series([1] * 99 + [0]))
    assert has_usable_class_balance(pd.Series([1] * 20 + [0] * 20))


def test_expanding_temporal_splits_use_later_non_overlapping_holdouts():
    features = pd.DataFrame({"value": list(range(10))})
    target = pd.Series(list(range(10)))
    timestamps = pd.Series(pd.date_range("2024-01-01", periods=10))

    splits = expanding_temporal_splits(features, target, timestamps, n_splits=3, test_size=0.2)

    assert [split[0]["value"].tolist() for split in splits] == [
        [0, 1, 2, 3],
        [0, 1, 2, 3, 4, 5],
        [0, 1, 2, 3, 4, 5, 6, 7],
    ]
    assert [split[1]["value"].tolist() for split in splits] == [
        [4, 5],
        [6, 7],
        [8, 9],
    ]
