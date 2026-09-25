"""
User segmentation.

Two approaches, deliberately kept side by side so the value-add of clustering
over simple rules can be judged directly rather than assumed:

1. RULE-BASED segmentation: simple, explainable thresholds on engagement
   (session count) and AI usage. Cheap to compute, easy to explain to a
   non-technical stakeholder.

2. K-MEANS clustering: behavioural features (sessions, AI usage, projects,
   documents, subscription) reduced to a small number of clusters, then each
   cluster is profiled and given a business interpretation. This is only
   worth using if it surfaces a segment or distinction the rule-based
   approach misses -- see compare_segmentations() below, which checks that.

Run:
    python src/segmentation/segment_users.py
"""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


def build_segmentation_features(users: pd.DataFrame, clean_events: pd.DataFrame,
                                 user_features: pd.DataFrame) -> pd.DataFrame:
    """One row per user: behavioural features used by both segmentation approaches."""
    df = clean_events.copy()

    n_sessions = df.groupby("user_id")["session_id"].nunique().rename("n_sessions")
    n_events = df.groupby("user_id").size().rename("n_events")
    n_active_days = df.assign(date=pd.to_datetime(df["timestamp"]).dt.date) \
                       .groupby("user_id")["date"].nunique().rename("n_active_days")
    n_projects = df[df["event_name"] == "project_created"].groupby("user_id").size().rename("n_projects")
    n_documents = df[df["event_name"] == "document_uploaded"].groupby("user_id").size().rename("n_documents")

    feats = user_features.copy()
    feats = feats.merge(n_sessions, on="user_id", how="left")
    feats = feats.merge(n_events, on="user_id", how="left")
    feats = feats.merge(n_active_days, on="user_id", how="left")
    feats = feats.merge(n_projects, on="user_id", how="left")
    feats = feats.merge(n_documents, on="user_id", how="left")

    for col in ["n_sessions", "n_events", "n_active_days", "n_projects", "n_documents"]:
        feats[col] = feats[col].fillna(0).astype(int)

    return feats


def rule_based_segments(feats: pd.DataFrame) -> pd.DataFrame:
    """Explainable thresholds, computed from this dataset's own distribution
    (median engagement) rather than hardcoded magic numbers -- so the tiers
    stay meaningful if you regenerate data at a different scale. 'Never
    activated' means no event beyond signup itself (n_events <= 1); every
    signup creates at least one session, so n_sessions alone can't detect
    true inactivity."""
    df = feats.copy()
    median_sessions = df.loc[df["n_events"] > 1, "n_sessions"].median()

    def _segment(row):
        if row["n_events"] <= 1:
            return "Never activated"
        if row["subscribed"] and row["n_sessions"] >= median_sessions:
            return "Power users"
        if row["ai_adopter"] and row["n_sessions"] < median_sessions:
            return "AI adopters (light)"
        if row["n_sessions"] >= median_sessions:
            return "Engaged non-AI"
        return "Explorers (low engagement)"

    df["rule_based_segment"] = df.apply(_segment, axis=1)
    return df


def kmeans_segments(feats: pd.DataFrame, n_clusters: int = 4, random_state: int = 42) -> pd.DataFrame:
    df = feats.copy()
    feature_cols = ["n_sessions", "n_events", "n_active_days", "n_projects",
                     "n_documents", "ai_query_count"]
    X = df[feature_cols].values
    X_scaled = StandardScaler().fit_transform(X)

    km = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    df["kmeans_cluster"] = km.fit_predict(X_scaled)
    return df, feature_cols


def profile_clusters(df: pd.DataFrame, feature_cols: list, cluster_col: str = "kmeans_cluster") -> pd.DataFrame:
    """Mean behavioural profile per cluster, plus retention/subscription rates,
    so clusters can be given a business interpretation rather than just a
    numeric label."""
    agg = df.groupby(cluster_col).agg(
        n_users=("user_id", "count"),
        **{f"avg_{c}": (c, "mean") for c in feature_cols},
        ai_adoption_pct=("ai_adopter", lambda x: round(100 * x.mean(), 1)),
        subscribed_pct=("subscribed", lambda x: round(100 * x.mean(), 1)),
        activated_pct=("activated", lambda x: round(100 * x.mean(), 1)),
    ).reset_index()
    for c in feature_cols:
        agg[f"avg_{c}"] = agg[f"avg_{c}"].round(2)
    return agg.sort_values("subscribed_pct", ascending=False)


def suggest_cluster_action(row: pd.Series, profile: pd.DataFrame) -> str:
    """Maps a cluster's profile to a suggested product action, using
    thresholds relative to this run's own cluster distribution (median
    subscription/AI-adoption/session rates across clusters) rather than
    hardcoded absolute percentages -- a fixed '>50% subscribed' threshold
    would never fire on a low-monetisation dataset like this one, which
    would silently produce identical, uninformative suggestions for every
    cluster. Deliberately simple -- this demonstrates the analytical
    reasoning step, not a production recommendation engine (that's Tier 3,
    see docs/roadmap.md)."""
    med_subscribed = profile["subscribed_pct"].median()
    med_ai = profile["ai_adoption_pct"].median()
    med_sessions = profile["avg_n_sessions"].median()

    if row["subscribed_pct"] >= med_subscribed and row["ai_adoption_pct"] >= med_ai:
        return "Power/AI users -> candidates for premium AI features, case studies, referral asks"
    if row["ai_adoption_pct"] >= med_ai and row["subscribed_pct"] < med_subscribed:
        return "High AI usage, low monetisation -> targeted upgrade prompts"
    if row["avg_n_sessions"] < med_sessions:
        return "Below-median engagement -> re-engagement campaign or onboarding improvement"
    return "Engaged but low AI usage -> nudge toward AI feature discovery"


def compare_segmentations(rule_df: pd.DataFrame, cluster_profile: pd.DataFrame) -> str:
    """A short, honest note on whether K-Means added anything the rule-based
    segments didn't already show -- avoids using clustering just to say
    'I used K-Means.'"""
    n_rule_segments = rule_df["rule_based_segment"].nunique()
    n_clusters = len(cluster_profile)
    subscribed_spread = cluster_profile["subscribed_pct"].max() - cluster_profile["subscribed_pct"].min()
    verdict = (
        f"Rule-based segmentation produced {n_rule_segments} explainable tiers. "
        f"K-Means (k={n_clusters}) found a {subscribed_spread:.1f}pp spread in subscription "
        f"rate across clusters. "
    )
    if subscribed_spread > 30:
        verdict += "This spread is wide enough that clustering surfaces a distinction the simple rules miss."
    else:
        verdict += "This spread is modest -- clustering mostly confirms what the simpler rule-based tiers already show."
    return verdict


if __name__ == "__main__":
    users = pd.read_csv("data/raw/users.csv", parse_dates=["signup_date"])
    clean_events = pd.read_csv("data/processed/clean_events.csv", parse_dates=["timestamp"])
    user_features = pd.read_csv("data/processed/user_features.csv")

    feats = build_segmentation_features(users, clean_events, user_features)

    print("=== Rule-based segments ===")
    rule_df = rule_based_segments(feats)
    print(rule_df["rule_based_segment"].value_counts().to_string())

    print("\n=== K-Means clusters (k=4) ===")
    cluster_df, feature_cols = kmeans_segments(feats, n_clusters=4)
    profile = profile_clusters(cluster_df, feature_cols)
    profile["suggested_action"] = profile.apply(lambda row: suggest_cluster_action(row, profile), axis=1)
    print(profile.to_string(index=False))

    print("\n=== Does clustering add value over rules? ===")
    print(compare_segmentations(rule_df, profile))
