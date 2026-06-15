import numpy as np
import pandas as pd


def temporal_train_test_split(features, target, timestamps, test_size=0.2):
    """Split aligned rows so the most recent observations form the holdout."""
    if not 0 < test_size < 1:
        raise ValueError("test_size must be between 0 and 1")
    if not len(features) == len(target) == len(timestamps):
        raise ValueError("features, target, and timestamps must have equal lengths")
    if len(features) < 2:
        raise ValueError("at least two rows are required for a temporal split")

    timestamp_values = pd.to_datetime(timestamps).to_numpy()
    order = np.argsort(timestamp_values)
    split_index = max(1, min(len(order) - 1, int(len(order) * (1 - test_size))))
    cutoff = timestamp_values[order[split_index]]
    ordered_timestamps = timestamp_values[order]
    train_index = order[ordered_timestamps < cutoff]
    test_index = order[ordered_timestamps >= cutoff]

    if not len(train_index) or not len(test_index):
        raise ValueError("timestamps must contain at least two distinct values")

    return (
        features.iloc[train_index],
        features.iloc[test_index],
        target.iloc[train_index],
        target.iloc[test_index],
    )


def has_usable_class_balance(target, minimum_share=0.05, minimum_count=20):
    """Return whether every class is sufficiently represented for evaluation."""
    counts = pd.Series(target).value_counts()
    if len(counts) < 2:
        return False
    return counts.min() >= minimum_count and counts.min() / counts.sum() >= minimum_share
