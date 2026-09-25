"""
North Star Metric + KPI hierarchy for InsightAI.

North Star: Weekly Active Users completing a meaningful AI-assisted task
  (defined here as: at least one ai_query_submitted event with a corresponding
  ai_response_received in the same week)

Run:
    python src/metrics/kpi.py
"""
import pandas as pd


def compute_north_star(clean_events: pd.DataFrame) -> pd.DataFrame:
    df = clean_events.copy()
    df["week"] = df["timestamp"].dt.to_period("W").astype(str)
    ai_task_users = (
        df[df["event_name"] == "ai_response_received"]
        .groupby("week")["user_id"].nunique()
        .rename("north_star_wau")
        .reset_index()
    )
    return ai_task_users


def compute_kpi_summary(users: pd.DataFrame, clean_events: pd.DataFrame, user_features: pd.DataFrame) -> dict:
    n_users = users["user_id"].nunique()
    df = clean_events

    summary = {
        # Acquisition
        "new_users": n_users,
        "signup_conversion_note": "requires pre-signup funnel data (landing page), not modeled here",

        # Activation
        "onboarding_completion_rate_pct": round(
            100 * user_features["activated"].mean(), 2
        ),

        # Engagement
        "dau_avg": round(df.groupby(df["timestamp"].dt.date)["user_id"].nunique().mean(), 1),
        "ai_interactions_per_user": round(
            (df["event_name"] == "ai_query_submitted").sum() / n_users, 2
        ),
        "ai_feature_penetration_pct": round(100 * user_features["ai_adopter"].mean(), 2),

        # Monetisation
        "free_to_paid_conversion_pct": round(100 * user_features["subscribed"].mean(), 2),

        # AI
        "ai_adoption_pct": round(100 * user_features["ai_adopter"].mean(), 2),
        "avg_ai_queries_per_adopter": round(
            user_features.loc[user_features["ai_adopter"], "ai_query_count"].mean(), 2
        ),
    }
    return summary


if __name__ == "__main__":
    users = pd.read_csv("data/raw/users.csv", parse_dates=["signup_date"])
    clean_events = pd.read_csv("data/processed/clean_events.csv", parse_dates=["timestamp"])
    user_features = pd.read_csv("data/processed/user_features.csv")

    print("=== North Star Metric (WAU completing AI task) ===")
    print(compute_north_star(clean_events).to_string(index=False))

    print("\n=== KPI Summary ===")
    for k, v in compute_kpi_summary(users, clean_events, user_features).items():
        print(f"{k}: {v}")
