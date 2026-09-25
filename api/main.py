
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

from metrics.funnel import compute_funnel
from metrics.retention import compute_retention_curve, compute_behavioural_cohort_comparison, compute_cohort_retention
from metrics.kpi import compute_kpi_summary, compute_north_star
from ai_analysis.ai_feature_metrics import compute_adoption, compute_quality, compute_cost
from business_impact.roi import compute_business_impact
from experimentation.ab_test import two_proportion_z_test, interpret
from experimentation.segment_experiment import segmented_ab_results, summarize_heterogeneity
from segmentation.segment_users import (
    build_segmentation_features, rule_based_segments, kmeans_segments,
    profile_clusters, suggest_cluster_action, compare_segmentations,
)
from recommendations.engine import generate_recommendations
from recommendations.rice_scoring import build_initiative_table

DATA_RAW = "data/raw"
DATA_PROCESSED = "data/processed"

app = FastAPI(
    title="InsightAI Product Analytics API",
    description="Analytics endpoints for the InsightAI product intelligence project. "
                "All data served is synthetically generated -- see project README.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # fine for a local/portfolio deployment; restrict in production
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _load_data():
    """Loads the processed/raw tables needed by most endpoints. Raises a
    clear 503-style error if the pipeline hasn't been run yet, rather than a
    confusing pandas FileNotFoundError traceback."""
    try:
        users = pd.read_csv(f"{DATA_RAW}/users.csv", parse_dates=["signup_date"])
        clean_events = pd.read_csv(f"{DATA_PROCESSED}/clean_events.csv", parse_dates=["timestamp"])
        user_features = pd.read_csv(f"{DATA_PROCESSED}/user_features.csv")
        return users, clean_events, user_features
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Data not found ({e.filename}). Run the data pipeline first: "
                    "python src/ingestion/generate_synthetic_data.py && "
                    "python src/preprocessing/etl.py",
        )


@app.get("/health")
def health():
    """Basic liveness check -- does not require the data pipeline to have run."""
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    """North Star metric + supporting KPI hierarchy."""
    users, clean_events, user_features = _load_data()
    kpis = compute_kpi_summary(users, clean_events, user_features)
    north_star = compute_north_star(clean_events).to_dict(orient="records")
    return {"kpi_summary": kpis, "north_star_weekly": north_star}


@app.get("/funnel")
def funnel(segment_by: str = Query(None, description="Optional column to segment by, e.g. 'experiment_group'")):
    """Onboarding/activation funnel, overall or segmented."""
    users, clean_events, _ = _load_data()
    if segment_by and segment_by not in users.columns:
        raise HTTPException(status_code=400, detail=f"Unknown segment_by column: {segment_by}")
    result = compute_funnel(clean_events, users=users, segment_col=segment_by)
    return result.to_dict(orient="records")


@app.get("/retention")
def retention(days: str = Query("1,7,14,30", description="Comma-separated list of days")):
    """D-day retention curve."""
    users, clean_events, _ = _load_data()
    day_list = [int(d) for d in days.split(",")]
    curve = compute_retention_curve(clean_events, users, days=tuple(day_list))
    return curve.to_dict(orient="records")


@app.get("/cohorts")
def cohorts():
    """Signup-month cohort retention matrix."""
    users, clean_events, _ = _load_data()
    result = compute_cohort_retention(clean_events, users)
    return result.to_dict(orient="records")


@app.get("/cohorts/behavioural")
def behavioural_cohorts(day: int = Query(30, description="Day to compare retention at")):
    """Behavioural cohort comparison (AI adopters vs not, activated vs not).
    Explicitly an observational association -- see /experiments for the
    causal comparison."""
    users, clean_events, user_features = _load_data()
    result = compute_behavioural_cohort_comparison(user_features, clean_events, users, day=day)
    return {
        "note": "Observational association, not a causal claim. See /experiments for the randomised comparison.",
        "data": result.to_dict(orient="records"),
    }


@app.get("/segments")
def segments(n_clusters: int = Query(4, ge=2, le=8)):
    """User segmentation: rule-based tiers + K-Means clusters with profiles."""
    users, clean_events, user_features = _load_data()
    feats = build_segmentation_features(users, clean_events, user_features)

    rule_df = rule_based_segments(feats)
    rule_counts = rule_df["rule_based_segment"].value_counts().to_dict()

    cluster_df, feature_cols = kmeans_segments(feats, n_clusters=n_clusters)
    profile = profile_clusters(cluster_df, feature_cols)
    profile["suggested_action"] = profile.apply(lambda row: suggest_cluster_action(row, profile), axis=1)

    return {
        "rule_based_segment_counts": rule_counts,
        "kmeans_cluster_profiles": profile.to_dict(orient="records"),
        "comparison_verdict": compare_segmentations(rule_df, profile),
    }


@app.get("/experiments")
def experiments(segment_by: str = Query(None, description="Optional: 'device', 'acquisition_channel', or 'country'")):
    """A/B test result (AI-assisted onboarding vs control), overall or
    segmented to check whether the effect holds across subgroups."""
    users, clean_events, _ = _load_data()

    if segment_by:
        if segment_by not in users.columns:
            raise HTTPException(status_code=400, detail=f"Unknown segment_by column: {segment_by}")
        seg_results = segmented_ab_results(users, clean_events, segment_by)
        verdict = summarize_heterogeneity(seg_results, segment_by)
        return {"segmented_by": segment_by, "results": seg_results.to_dict(orient="records"), "heterogeneity_verdict": verdict}

    activated_users = set(clean_events.loc[clean_events["event_name"] == "onboarding_completed", "user_id"])
    df = users.copy()
    df["activated"] = df["user_id"].isin(activated_users)
    control = df[df["experiment_group"] == "control"]
    treatment = df[df["experiment_group"] == "treatment"]
    result = two_proportion_z_test(
        success_a=int(control["activated"].sum()), n_a=len(control),
        success_b=int(treatment["activated"].sum()), n_b=len(treatment),
    )
    result["interpretation"] = interpret(result)
    return result


@app.get("/ai-feature")
def ai_feature():
    """AI feature adoption, quality proxy metrics, and cost."""
    _, clean_events, user_features = _load_data()
    return {
        "adoption": compute_adoption(user_features),
        "quality": compute_quality(clean_events),
        "cost": compute_cost(clean_events, user_features),
    }


@app.get("/business-impact")
def business_impact():
    """Revenue vs. AI cost, ROI."""
    _, clean_events, user_features = _load_data()
    ai_cost = compute_cost(clean_events, user_features)
    return compute_business_impact(user_features, ai_cost)


@app.get("/recommendations")
def recommendations(segment_by: str = Query("device", description="Column used for the heterogeneity caveat check")):
    """Rule-based recommendations, each with its triggering evidence attached.
    Surfaces evidence and a suggested action -- does not replace product-manager
    judgement (see src/recommendations/engine.py docstring)."""
    users, clean_events, user_features = _load_data()
    funnel_df = compute_funnel(clean_events, users=users)

    activated_users = set(clean_events.loc[clean_events["event_name"] == "onboarding_completed", "user_id"])
    df = users.copy()
    df["activated"] = df["user_id"].isin(activated_users)
    control = df[df["experiment_group"] == "control"]
    treatment = df[df["experiment_group"] == "treatment"]
    ab_result = two_proportion_z_test(
        success_a=int(control["activated"].sum()), n_a=len(control),
        success_b=int(treatment["activated"].sum()), n_b=len(treatment),
    )

    heterogeneity_note = None
    if segment_by in users.columns:
        seg_results = segmented_ab_results(users, clean_events, segment_by)
        heterogeneity_note = summarize_heterogeneity(seg_results, segment_by)

    adoption = compute_adoption(user_features)
    ai_cost = compute_cost(clean_events, user_features)
    impact = compute_business_impact(user_features, ai_cost)

    recs = generate_recommendations(funnel_df, ab_result, adoption, impact, heterogeneity_note)
    return {"recommendations": recs, "heterogeneity_note": heterogeneity_note}


@app.get("/rice-roadmap")
def rice_roadmap():
    """RICE-scored hypothetical roadmap. Reach/Confidence for the onboarding
    initiative are grounded in real project data; the rest are disclosed
    analyst estimates -- see confidence_basis in each row."""
    users, clean_events, _ = _load_data()
    funnel_df = compute_funnel(clean_events, users=users)

    activated_users = set(clean_events.loc[clean_events["event_name"] == "onboarding_completed", "user_id"])
    df = users.copy()
    df["activated"] = df["user_id"].isin(activated_users)
    control = df[df["experiment_group"] == "control"]
    treatment = df[df["experiment_group"] == "treatment"]
    ab_result = two_proportion_z_test(
        success_a=int(control["activated"].sum()), n_a=len(control),
        success_b=int(treatment["activated"].sum()), n_b=len(treatment),
    )

    table = build_initiative_table(funnel_df, ab_result, total_users=len(users))
    return {
        "note": "Impact/Effort and 4 of 5 Confidence values are disclosed analyst estimates, not measured quantities.",
        "roadmap": table.to_dict(orient="records"),
    }
