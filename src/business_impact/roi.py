"""
Business impact: incremental revenue vs incremental AI cost, ROI.

Revenue assumption: a fixed ARPU for subscribed ("pro") users. This is a modeling
choice, clearly disclosed -- replace with real pricing data in a production version.

Run:
    python src/business_impact/roi.py
"""
import pandas as pd

MONTHLY_ARPU_USD = 29.0  # ASSUMPTION: illustrative "pro" plan price


def compute_business_impact(user_features: pd.DataFrame, ai_cost_summary: dict) -> dict:
    subscribed_ai_adopters = user_features[
        user_features["subscribed"] & user_features["ai_adopter"]
    ]
    subscribed_non_adopters = user_features[
        user_features["subscribed"] & ~user_features["ai_adopter"]
    ]

    # Illustrative revenue attribution: all subscribed users generate ARPU;
    # we are NOT claiming AI caused the subscription (see README methodology note) --
    # this is a simple revenue/cost side-by-side, not an attribution model.
    total_pro_users = user_features["subscribed"].sum()
    total_revenue = total_pro_users * MONTHLY_ARPU_USD
    total_ai_cost = ai_cost_summary["total_ai_cost_usd"]

    roi_pct = round(100 * (total_revenue - total_ai_cost) / total_ai_cost, 1) if total_ai_cost else None

    return {
        "total_pro_users": int(total_pro_users),
        "total_monthly_revenue_usd": round(total_revenue, 2),
        "total_ai_cost_usd": round(total_ai_cost, 2),
        "ai_cost_as_pct_of_revenue": round(100 * total_ai_cost / total_revenue, 2) if total_revenue else None,
        "roi_pct": roi_pct,
        "subscribed_ai_adopters": len(subscribed_ai_adopters),
        "subscribed_non_ai_adopters": len(subscribed_non_adopters),
        "note": "Revenue is illustrative ARPU-based, not attributed causally to AI usage. "
                "See README methodological rule.",
    }


if __name__ == "__main__":
    import sys
    sys.path.append("src")
    from ai_analysis.ai_feature_metrics import compute_cost

    clean_events = pd.read_csv("data/processed/clean_events.csv", parse_dates=["timestamp"])
    user_features = pd.read_csv("data/processed/user_features.csv")

    ai_cost = compute_cost(clean_events, user_features)
    impact = compute_business_impact(user_features, ai_cost)

    print("=== Business Impact ===")
    for k, v in impact.items():
        print(f"{k}: {v}")
