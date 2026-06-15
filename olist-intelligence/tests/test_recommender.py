"""Recommender artifact and offline evaluation tests."""

import pandas as pd

from src.ml.recommender import (
    build_recommender_artifact,
    evaluate_leave_one_out,
    recommend_from_artifact,
)


def _interactions():
    return pd.DataFrame(
        {
            "customer_id": ["u1", "u1", "u2", "u2", "u3", "u3"],
            "product_id": ["p1", "p2", "p1", "p3", "p2", "p3"],
            "purchase_count": [1, 1, 1, 1, 1, 1],
        }
    )


def test_recommendations_exclude_seen_products():
    artifact = build_recommender_artifact(_interactions())

    recommendations = recommend_from_artifact(artifact, "u1", top_k=3)

    assert recommendations == ["p3"]


def test_unknown_user_has_no_personalized_recommendations():
    artifact = build_recommender_artifact(_interactions())

    assert recommend_from_artifact(artifact, "unknown") == []


def test_leave_one_out_evaluation_returns_bounded_metrics():
    result = evaluate_leave_one_out(_interactions(), top_k=2)

    assert result["users_evaluated"] > 0
    assert 0 <= result["hit_rate_at_k"] <= 1
    assert 0 <= result["catalog_coverage_at_k"] <= 1
