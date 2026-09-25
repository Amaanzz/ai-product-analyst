"""
AI Feature Analytics: adoption, quality, cost.

Cost model note: real token/cost data isn't in the synthetic event stream, so a
simple, clearly-labelled assumption is used: a fixed estimated cost per AI query.
Swap COST_PER_QUERY_USD for real billing data in a production version.

Run:
    python src/ai_analysis/ai_feature_metrics.py
"""
import pandas as pd

COST_PER_QUERY_USD = 0.012  # ASSUMPTION: illustrative, not a real billing figure


def compute_adoption(user_features: pd.DataFrame) -> dict:
    n_users = len(user_features)
    n_adopters = user_features["ai_adopter"].sum()
    return {
        "ai_adoption_pct": round(100 * n_adopters / n_users, 2),
        "n_adopters": int(n_adopters),
        "avg_queries_per_adopter": round(
            user_features.loc[user_features["ai_adopter"], "ai_query_count"].mean(), 2
        ),
    }


def compute_quality(clean_events: pd.DataFrame) -> dict:
    n_queries = (clean_events["event_name"] == "ai_query_submitted").sum()
    n_responses = (clean_events["event_name"] == "ai_response_received").sum()
    n_ratings = (clean_events["event_name"] == "ai_response_rated").sum()
    return {
        "ai_queries_total": int(n_queries),
        "ai_responses_total": int(n_responses),
        "response_rate_pct": round(100 * n_responses / n_queries, 2) if n_queries else None,
        "rating_rate_pct": round(100 * n_ratings / n_responses, 2) if n_responses else None,
        "note": "response_rate_pct is a proxy for reliability; rating_rate_pct is a proxy "
                "for engagement with feedback, not a satisfaction score (no rating value is "
                "simulated in this dataset -- see docs/roadmap.md for adding thumbs up/down).",
    }


def compute_cost(clean_events: pd.DataFrame, user_features: pd.DataFrame) -> dict:
    n_queries = (clean_events["event_name"] == "ai_query_submitted").sum()
    total_cost = n_queries * COST_PER_QUERY_USD
    n_users = len(user_features)
    n_adopters = user_features["ai_adopter"].sum()
    n_retained_and_adopted = int(((user_features["ai_adopter"]) & (user_features["subscribed"])).sum())

    return {
        "total_ai_cost_usd": round(total_cost, 2),
        "cost_per_user_usd": round(total_cost / n_users, 4),
        "cost_per_adopter_usd": round(total_cost / n_adopters, 4) if n_adopters else None,
        "cost_per_subscribed_ai_adopter_usd": round(total_cost / n_retained_and_adopted, 4)
        if n_retained_and_adopted else None,
        "cost_per_query_usd_assumption": COST_PER_QUERY_USD,
    }


if __name__ == "__main__":
    clean_events = pd.read_csv("data/processed/clean_events.csv", parse_dates=["timestamp"])
    user_features = pd.read_csv("data/processed/user_features.csv")

    print("=== AI Adoption ===")
    print(compute_adoption(user_features))

    print("\n=== AI Quality (proxy metrics) ===")
    print(compute_quality(clean_events))

    print("\n=== AI Cost ===")
    print(compute_cost(clean_events, user_features))
