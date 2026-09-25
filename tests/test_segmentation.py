"""
Tests for user segmentation (rule-based + K-Means).
Run: pytest tests/test_segmentation.py
"""
import sys
sys.path.append(".")

import pandas as pd
from src.segmentation.segment_users import (
    build_segmentation_features, rule_based_segments, kmeans_segments,
    profile_clusters, suggest_cluster_action,
)


def _sample_feats():
    return pd.DataFrame({
        "user_id": ["u1", "u2", "u3", "u4"],
        "activated": [True, True, False, True],
        "ai_adopter": [True, False, False, True],
        "subscribed": [True, False, False, True],
        "ai_query_count": [10, 0, 0, 20],
        "ai_rating_count": [2, 0, 0, 5],
        "n_sessions": [15, 6, 1, 20],
        "n_events": [30, 10, 1, 40],
        "n_active_days": [15, 6, 1, 18],
        "n_projects": [2, 1, 0, 3],
        "n_documents": [1, 0, 0, 2],
    })


def test_never_activated_detected():
    feats = _sample_feats()
    result = rule_based_segments(feats)
    u3_segment = result.loc[result["user_id"] == "u3", "rule_based_segment"].iloc[0]
    assert u3_segment == "Never activated"


def test_all_rows_get_a_segment():
    feats = _sample_feats()
    result = rule_based_segments(feats)
    assert result["rule_based_segment"].notna().all()


def test_kmeans_produces_requested_cluster_count():
    feats = _sample_feats()
    # duplicate rows to have enough samples for k=2 clustering
    feats = pd.concat([feats] * 5, ignore_index=True)
    feats["user_id"] = [f"u{i}" for i in range(len(feats))]
    cluster_df, feature_cols = kmeans_segments(feats, n_clusters=2)
    assert cluster_df["kmeans_cluster"].nunique() <= 2


def test_profile_clusters_has_expected_columns():
    feats = _sample_feats()
    feats = pd.concat([feats] * 5, ignore_index=True)
    feats["user_id"] = [f"u{i}" for i in range(len(feats))]
    cluster_df, feature_cols = kmeans_segments(feats, n_clusters=2)
    profile = profile_clusters(cluster_df, feature_cols)
    assert "subscribed_pct" in profile.columns
    assert "ai_adoption_pct" in profile.columns


def test_suggest_action_varies_with_relative_thresholds():
    profile = pd.DataFrame({
        "kmeans_cluster": [0, 1],
        "subscribed_pct": [25.0, 0.5],
        "ai_adoption_pct": [90.0, 1.0],
        "avg_n_sessions": [14.0, 3.0],
    })
    action_0 = suggest_cluster_action(profile.iloc[0], profile)
    action_1 = suggest_cluster_action(profile.iloc[1], profile)
    assert action_0 != action_1
