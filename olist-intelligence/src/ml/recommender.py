"""Recommender artifact construction, inference, and offline evaluation."""

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD


def build_recommender_artifact(interactions: pd.DataFrame) -> dict:
    """Build a deterministic sparse SVD artifact from user-product interactions."""
    required = {"customer_id", "product_id", "purchase_count"}
    missing = required.difference(interactions.columns)
    if missing:
        raise ValueError(f"Missing recommender columns: {sorted(missing)}")
    if interactions.empty:
        raise ValueError("Recommender interactions cannot be empty")

    frame = interactions.copy()
    user_ids = sorted(frame["customer_id"].unique())
    product_ids = sorted(frame["product_id"].unique())
    user_map = {value: index for index, value in enumerate(user_ids)}
    product_map = {value: index for index, value in enumerate(product_ids)}
    reverse_product_map = {index: value for value, index in product_map.items()}
    frame["user_idx"] = frame["customer_id"].map(user_map)
    frame["product_idx"] = frame["product_id"].map(product_map)

    matrix_sparse = csr_matrix(
        (
            frame["purchase_count"].values,
            (frame["user_idx"].values, frame["product_idx"].values),
        ),
        shape=(len(user_ids), len(product_ids)),
    )
    max_components = min(matrix_sparse.shape) - 1
    if max_components < 1:
        raise ValueError("Recommender requires at least two users and two products")
    svd = TruncatedSVD(n_components=min(20, max_components), random_state=42)
    matrix_reduced = svd.fit_transform(matrix_sparse)

    return {
        "model": svd,
        "matrix_reduced": matrix_reduced,
        "product_components": svd.components_,
        "user_map": user_map,
        "product_map": product_map,
        "reverse_product_map": reverse_product_map,
        "seen_product_indices": (
            frame.groupby("customer_id")["product_idx"]
            .apply(lambda values: values.astype(int).tolist())
            .to_dict()
        ),
    }


def recommend_from_artifact(artifact: dict, customer_id: str, top_k: int = 5) -> list[str]:
    """Return unseen product IDs for a known user."""
    if customer_id not in artifact.get("user_map", {}):
        return []
    user_idx = artifact["user_map"][customer_id]
    scores = artifact["matrix_reduced"][user_idx] @ artifact["product_components"]
    seen = set(artifact.get("seen_product_indices", {}).get(customer_id, []))
    ranked_indices = [int(index) for index in np.argsort(scores)[::-1] if int(index) not in seen]
    return [
        artifact["reverse_product_map"][index]
        for index in ranked_indices[:top_k]
        if index in artifact["reverse_product_map"]
    ]


def evaluate_leave_one_out(interactions: pd.DataFrame, top_k: int = 10) -> dict[str, float]:
    """Measure hit rate and catalog coverage on one held-out product per repeat user."""
    ordered = interactions.sort_values(["customer_id", "product_id"]).copy()
    repeat_users = ordered.groupby("customer_id")["product_id"].nunique()
    repeat_users = set(repeat_users[repeat_users >= 2].index)
    evaluation_rows = ordered[ordered["customer_id"].isin(repeat_users)]
    holdout = evaluation_rows.groupby("customer_id").tail(1)
    train = ordered.drop(index=holdout.index)
    artifact = build_recommender_artifact(train)

    held_out_by_user = dict(zip(holdout["customer_id"], holdout["product_id"]))
    eligible_users = [
        user_id
        for user_id, product_id in held_out_by_user.items()
        if user_id in artifact["user_map"] and product_id in artifact["product_map"]
    ]
    if not eligible_users:
        return {"users_evaluated": 0, "hit_rate_at_k": 0.0, "catalog_coverage_at_k": 0.0}

    recommendation_lists = [
        recommend_from_artifact(artifact, user_id, top_k=top_k)
        for user_id in eligible_users
    ]
    hits = sum(
        held_out_by_user[user_id] in recommendations
        for user_id, recommendations in zip(eligible_users, recommendation_lists)
    )
    recommended_products = {product for values in recommendation_lists for product in values}
    return {
        "users_evaluated": len(eligible_users),
        "hit_rate_at_k": hits / len(eligible_users),
        "catalog_coverage_at_k": len(recommended_products) / len(artifact["product_map"]),
    }
