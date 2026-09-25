"""
Tests for src/recommendations/engine.py and src/recommendations/rice_scoring.py.
Run: pytest tests/test_recommendations.py
"""
import sys
sys.path.append(".")
sys.path.append("src")

import pandas as pd
from src.recommendations.engine import generate_recommendations
from src.recommendations.rice_scoring import score_rice, build_initiative_table


def _sample_funnel():
    return pd.DataFrame([
        {"stage": "signup", "users_reached": 1000, "conversion_from_previous_pct": 100.0, "conversion_from_start_pct": 100.0},
        {"stage": "onboarding_started", "users_reached": 800, "conversion_from_previous_pct": 80.0, "conversion_from_start_pct": 80.0},
        {"stage": "onboarding_completed", "users_reached": 300, "conversion_from_previous_pct": 37.5, "conversion_from_start_pct": 30.0},
        {"stage": "project_created", "users_reached": 250, "conversion_from_previous_pct": 83.3, "conversion_from_start_pct": 25.0},
        {"stage": "ai_assistant_opened", "users_reached": 100, "conversion_from_previous_pct": 40.0, "conversion_from_start_pct": 10.0},
        {"stage": "output_saved", "users_reached": 80, "conversion_from_previous_pct": 80.0, "conversion_from_start_pct": 8.0},
    ])


def test_biggest_dropoff_flagged():
    funnel = _sample_funnel()
    ab_result = {"p_value": 0.5, "absolute_lift_pp": 1.0, "ci_95_absolute_lift_pp": (-2, 4)}
    adoption = {"ai_adoption_pct": 10}
    impact = {"roi_pct": -10}
    recs = generate_recommendations(funnel, ab_result, adoption, impact)
    dropoff_recs = [r for r in recs if "onboarding_completed" in r["trigger"]]
    assert len(dropoff_recs) == 1
    assert dropoff_recs[0]["confidence"] == "High"


def test_significant_ab_result_recommends_rollout():
    funnel = _sample_funnel()
    ab_result = {
        "p_value": 0.001, "absolute_lift_pp": 9.0,
        "ci_95_absolute_lift_pp": (5.0, 13.0),
        "control_rate_pct": 50.0, "treatment_rate_pct": 59.0, "cohens_h": 0.18,
    }
    adoption = {"ai_adoption_pct": 25}
    impact = {"roi_pct": 100}
    recs = generate_recommendations(funnel, ab_result, adoption, impact)
    rollout_recs = [r for r in recs if "Roll out" in r["recommendation"]]
    assert len(rollout_recs) == 1
    assert rollout_recs[0]["confidence"] == "High"


def test_nonsignificant_ab_result_recommends_against_rollout():
    funnel = _sample_funnel()
    ab_result = {"p_value": 0.6, "absolute_lift_pp": 0.5, "ci_95_absolute_lift_pp": (-3, 4)}
    adoption = {"ai_adoption_pct": 25}
    impact = {"roi_pct": 100}
    recs = generate_recommendations(funnel, ab_result, adoption, impact)
    hold_recs = [r for r in recs if "Do not roll out" in r["recommendation"]]
    assert len(hold_recs) == 1


def test_heterogeneity_caveat_lowers_confidence():
    funnel = _sample_funnel()
    ab_result = {
        "p_value": 0.001, "absolute_lift_pp": 9.0,
        "ci_95_absolute_lift_pp": (5.0, 13.0),
        "control_rate_pct": 50.0, "treatment_rate_pct": 59.0, "cohens_h": 0.18,
    }
    adoption = {"ai_adoption_pct": 25}
    impact = {"roi_pct": 100}
    recs_no_caveat = generate_recommendations(funnel, ab_result, adoption, impact, heterogeneity_note="consistent everywhere")
    recs_with_caveat = generate_recommendations(funnel, ab_result, adoption, impact,
                                                 heterogeneity_note="one segment shows a lift in the opposite direction")
    conf_no_caveat = [r["confidence"] for r in recs_no_caveat if "Roll out" in r["recommendation"]][0]
    conf_with_caveat = [r["confidence"] for r in recs_with_caveat if "Roll out" in r["recommendation"]][0]
    assert conf_no_caveat == "High"
    assert conf_with_caveat == "Medium"


def test_rice_score_formula():
    # reach=1000, impact=2, confidence=0.8, effort=4 -> (1000*2*0.8)/4 = 400
    assert score_rice(1000, 2, 0.8, 4) == 400.0


def test_rice_score_rejects_zero_effort():
    try:
        score_rice(1000, 2, 0.8, 0)
        assert False, "should have raised"
    except ValueError:
        pass


def test_rice_table_is_sorted_descending():
    funnel = _sample_funnel()
    ab_result = {"p_value": 0.001, "absolute_lift_pp": 9.0}
    table = build_initiative_table(funnel, ab_result, total_users=1000)
    scores = table["rice_score"].tolist()
    assert scores == sorted(scores, reverse=True)


def test_rice_table_has_confidence_basis_for_every_row():
    funnel = _sample_funnel()
    ab_result = {"p_value": 0.001, "absolute_lift_pp": 9.0}
    table = build_initiative_table(funnel, ab_result, total_users=1000)
    assert table["confidence_basis"].notna().all()
    assert len(table) == 5
