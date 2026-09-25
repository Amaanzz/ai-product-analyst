"""
Tests for experiment segmentation (src/experimentation/segment_experiment.py).
Run: pytest tests/test_segment_experiment.py
"""
import sys
sys.path.append(".")
sys.path.append("src")

import pandas as pd
from src.experimentation.segment_experiment import segmented_ab_results, summarize_heterogeneity


def _sample_data():
    users = pd.DataFrame({
        "user_id": [f"u{i}" for i in range(200)],
        "experiment_group": (["control"] * 100 + ["treatment"] * 100),
        "device": (["desktop"] * 50 + ["mobile"] * 50) * 2,
    })
    # Treatment activates more often on desktop, same on mobile
    activated_ids = []
    activated_ids += [f"u{i}" for i in range(0, 20)]     # control desktop: 20/50
    activated_ids += [f"u{i}" for i in range(50, 70)]    # control mobile: 20/50
    activated_ids += [f"u{i}" for i in range(100, 140)]  # treatment desktop: 40/50
    activated_ids += [f"u{i}" for i in range(150, 170)]  # treatment mobile: 20/50
    events = pd.DataFrame({
        "user_id": activated_ids,
        "event_name": ["onboarding_completed"] * len(activated_ids),
    })
    return users, events


def test_segmented_results_has_expected_columns():
    users, events = _sample_data()
    result = segmented_ab_results(users, events, "device")
    assert "absolute_lift_pp" in result.columns
    assert set(result["device"]) == {"desktop", "mobile"}


def test_small_sample_flagged_not_computed():
    users = pd.DataFrame({
        "user_id": [f"u{i}" for i in range(10)],
        "experiment_group": ["control"] * 5 + ["treatment"] * 5,
        "device": ["desktop"] * 10,
    })
    events = pd.DataFrame({"user_id": [], "event_name": []})
    result = segmented_ab_results(users, events, "device")
    assert "note" in result.columns
    assert "small" in result["note"].iloc[0]


def test_heterogeneity_detects_reversed_effect():
    df = pd.DataFrame({
        "device": ["desktop", "mobile"],
        "absolute_lift_pp": [15.0, -2.0],
        "p_value": [0.01, 0.6],
    })
    verdict = summarize_heterogeneity(df, "device")
    assert "opposite direction" in verdict


def test_heterogeneity_consistent_effect():
    df = pd.DataFrame({
        "device": ["desktop", "mobile"],
        "absolute_lift_pp": [9.0, 8.0],
        "p_value": [0.01, 0.02],
    })
    verdict = summarize_heterogeneity(df, "device")
    assert "consistent" in verdict
