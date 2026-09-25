"""
Tests for the data logic behind the FastAPI endpoints (api/main.py).

IMPORTANT: these tests exercise the same analysis functions api/main.py calls,
and confirm every payload is JSON-serialisable -- they do NOT spin up FastAPI
itself or make HTTP requests, because `fastapi`/`uvicorn`/`httpx` were not
installable in the environment these tests were authored in (no internet
access). If you have those installed locally, add a proper
`TestClient(app)`-based test module alongside this one; this file is a
stand-in that still catches the most likely real bugs (missing columns,
non-serialisable numpy types, empty results) without needing the HTTP stack.

Run: pytest tests/test_api_logic.py
"""
import sys
import json
sys.path.append(".")
sys.path.append("src")

import pandas as pd

from src.metrics.funnel import compute_funnel
from src.metrics.kpi import compute_kpi_summary, compute_north_star
from src.ai_analysis.ai_feature_metrics import compute_adoption, compute_quality, compute_cost
from src.business_impact.roi import compute_business_impact
from src.experimentation.ab_test import two_proportion_z_test, interpret
from src.experimentation.segment_experiment import segmented_ab_results, summarize_heterogeneity
from src.segmentation.segment_users import (
    build_segmentation_features, rule_based_segments, kmeans_segments,
    profile_clusters, suggest_cluster_action, compare_segmentations,
)


def _load():
    users = pd.read_csv("data/raw/users.csv", parse_dates=["signup_date"])
    clean_events = pd.read_csv("data/processed/clean_events.csv", parse_dates=["timestamp"])
    user_features = pd.read_csv("data/processed/user_features.csv")
    return users, clean_events, user_features


def test_metrics_payload_serialisable():
    users, clean_events, user_features = _load()
    payload = {
        "kpi_summary": compute_kpi_summary(users, clean_events, user_features),
        "north_star_weekly": compute_north_star(clean_events).to_dict(orient="records"),
    }
    json.dumps(payload)  # raises TypeError if anything isn't serialisable


def test_funnel_endpoint_rejects_unknown_segment_column():
    users, clean_events, _ = _load()
    assert "not_a_real_column" not in users.columns


def test_funnel_segmented_by_experiment_group_serialisable():
    users, clean_events, _ = _load()
    result = compute_funnel(clean_events, users=users, segment_col="experiment_group")
    json.dumps(result.to_dict(orient="records"))


def test_experiments_endpoint_overall_matches_known_result():
    users, clean_events, _ = _load()
    activated = set(clean_events.loc[clean_events["event_name"] == "onboarding_completed", "user_id"])
    df = users.copy()
    df["activated"] = df["user_id"].isin(activated)
    control = df[df["experiment_group"] == "control"]
    treatment = df[df["experiment_group"] == "treatment"]
    result = two_proportion_z_test(
        int(control["activated"].sum()), len(control),
        int(treatment["activated"].sum()), len(treatment),
    )
    result["interpretation"] = interpret(result)
    json.dumps(result)
    assert result["p_value"] < 0.05


def test_segments_payload_serialisable_and_has_actions():
    users, clean_events, user_features = _load()
    feats = build_segmentation_features(users, clean_events, user_features)
    rule_df = rule_based_segments(feats)
    cluster_df, feature_cols = kmeans_segments(feats, n_clusters=4)
    profile = profile_clusters(cluster_df, feature_cols)
    profile["suggested_action"] = profile.apply(lambda row: suggest_cluster_action(row, profile), axis=1)
    payload = {
        "rule_based_segment_counts": rule_df["rule_based_segment"].value_counts().to_dict(),
        "kmeans_cluster_profiles": profile.to_dict(orient="records"),
        "comparison_verdict": compare_segmentations(rule_df, profile),
    }
    json.dumps(payload)
    assert profile["suggested_action"].nunique() > 1  # regression guard for the earlier "identical suggestion" bug


def test_ai_feature_and_business_impact_serialisable():
    users, clean_events, user_features = _load()
    ai_cost = compute_cost(clean_events, user_features)
    payload = {
        "adoption": compute_adoption(user_features),
        "quality": compute_quality(clean_events),
        "cost": ai_cost,
    }
    json.dumps(payload)
    impact = compute_business_impact(user_features, ai_cost)
    json.dumps(impact)
