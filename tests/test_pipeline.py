"""
Basic tests for the ETL, metrics, and A/B test modules.
Run: pytest tests/
"""
import sys
sys.path.append("src")
sys.path.append(".")

import pandas as pd
import pytest

from src.experimentation.ab_test import two_proportion_z_test, required_sample_size
from src.preprocessing.etl import clean_events


def test_clean_events_removes_duplicates():
    df = pd.DataFrame({
        "event_id": ["a", "a", "b"],
        "user_id": ["u1", "u1", "u2"],
        "timestamp": pd.to_datetime(["2025-01-01", "2025-01-01", "2025-01-02"]),
        "event_name": ["signup", "signup", "signup"],
        "session_id": ["s1", "s1", "s2"],
        "platform": ["desktop", "desktop", "mobile"],
        "feature": [None, None, None],
        "experiment_group": ["control", "control", "treatment"],
    })
    result = clean_events(df)
    assert len(result) == 2


def test_clean_events_removes_missing_user_id():
    df = pd.DataFrame({
        "event_id": ["a", "b"],
        "user_id": ["u1", None],
        "timestamp": pd.to_datetime(["2025-01-01", "2025-01-02"]),
        "event_name": ["signup", "signup"],
        "session_id": ["s1", "s2"],
        "platform": ["desktop", "mobile"],
        "feature": [None, None],
        "experiment_group": ["control", "treatment"],
    })
    result = clean_events(df)
    assert len(result) == 1


def test_clean_events_removes_invalid_timestamps():
    df = pd.DataFrame({
        "event_id": ["a", "b"],
        "user_id": ["u1", "u2"],
        "timestamp": pd.to_datetime(["2025-01-01", "2099-01-01"]),
        "event_name": ["signup", "signup"],
        "session_id": ["s1", "s2"],
        "platform": ["desktop", "mobile"],
        "feature": [None, None],
        "experiment_group": ["control", "treatment"],
    })
    result = clean_events(df)
    assert len(result) == 1


def test_two_proportion_z_test_no_difference():
    result = two_proportion_z_test(success_a=500, n_a=1000, success_b=500, n_b=1000)
    assert result["absolute_lift_pp"] == 0.0
    assert result["p_value"] > 0.05


def test_two_proportion_z_test_clear_difference():
    result = two_proportion_z_test(success_a=400, n_a=1000, success_b=600, n_b=1000)
    assert result["absolute_lift_pp"] == pytest.approx(20.0, abs=0.01)
    assert result["p_value"] < 0.05


def test_required_sample_size_reasonable_magnitude():
    n = required_sample_size(baseline_rate=0.62, min_detectable_effect=0.05)
    assert 500 < n < 5000  # sanity bounds, not an exact expected value
