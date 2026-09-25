
import pandas as pd


def score_rice(reach: int, impact: float, confidence: float, effort: float) -> float:
    """impact: 0.25 (minimal) / 0.5 (low) / 1 (medium) / 2 (high) / 3 (massive) -- standard RICE scale
    confidence: 0-1 (as a fraction, e.g. 0.8 = 80%)
    effort: person-months (or any consistent unit) -- smaller = less costly to build
    """
    if effort <= 0:
        raise ValueError("effort must be > 0")
    return round((reach * impact * confidence) / effort, 1)


def build_initiative_table(funnel_df: pd.DataFrame, ab_result: dict, total_users: int) -> pd.DataFrame:
    """Builds the 5 hypothetical initiatives from the original project brief,
    with Reach and Confidence grounded in real numbers where the project's
    own data can inform them, and Impact/Effort left as clearly-labelled
    analyst estimates."""

    output_saved_row = funnel_df[funnel_df["stage"] == "output_saved"]
    onboarding_row = funnel_df[funnel_df["stage"] == "onboarding_started"]
    ai_opened_row = funnel_df[funnel_df["stage"] == "ai_assistant_opened"]

    # Reach: how many users/quarter this initiative could plausibly touch,
    # grounded in the actual funnel counts where relevant.
    reach_onboarding = int(onboarding_row["users_reached"].iloc[0]) if not onboarding_row.empty else total_users
    reach_ai_expand = int(ai_opened_row["users_reached"].iloc[0]) if not ai_opened_row.empty else total_users
    reach_latency = int(ai_opened_row["users_reached"].iloc[0]) if not ai_opened_row.empty else total_users

    # Confidence: grounded in the A/B result where an initiative IS the tested
    # intervention; otherwise a stated analyst estimate (labelled as such).
    ab_confidence = 0.9 if ab_result.get("p_value", 1) < 0.05 else 0.4

    initiatives = [
        {
            "initiative": "Improve onboarding (address the largest funnel drop-off)",
            "reach": reach_onboarding,
            "impact": 2,       # high -- estimate, labelled below
            "confidence": ab_confidence,  # grounded: this IS what the A/B test tested
            "effort": 2,       # person-months -- estimate
            "confidence_basis": "Grounded in the A/B experiment result (Section 3.7)",
        },
        {
            "initiative": "Expand AI assistant capabilities",
            "reach": reach_ai_expand,
            "impact": 2,
            "confidence": 0.6,  # estimate -- no direct experiment tests "expanded capabilities"
            "effort": 4,
            "confidence_basis": "Analyst estimate -- not directly tested by any experiment in this project",
        },
        {
            "initiative": "Reduce AI response latency",
            "reach": reach_latency,
            "impact": 1,
            "confidence": 0.5,
            "effort": 3,
            "confidence_basis": (
                "Analyst estimate -- latency isn't measured in this dataset at all "
                "(see docs/project_specification.md, Section 12)"
            ),
        },
        {
            "initiative": "Improve collaboration features",
            "reach": int(total_users * 0.08),  # matches collaboration_invited's simulated ~8% rate
            "impact": 0.5,
            "confidence": 0.5,
            "effort": 3,
            "confidence_basis": "Analyst estimate -- low reach observed (collaboration_invited fires for ~8% of users)",
        },
        {
            "initiative": "Improve pricing page / conversion flow",
            "reach": total_users,
            "impact": 1,
            "confidence": 0.4,
            "effort": 2,
            "confidence_basis": "Analyst estimate -- no pricing-page-specific data exists in this project's event schema",
        },
    ]

    df = pd.DataFrame(initiatives)
    df["rice_score"] = df.apply(lambda r: score_rice(r["reach"], r["impact"], r["confidence"], r["effort"]), axis=1)
    return df.sort_values("rice_score", ascending=False).reset_index(drop=True)


if __name__ == "__main__":
    import sys
    sys.path.append("src")
    from metrics.funnel import compute_funnel
    from experimentation.ab_test import two_proportion_z_test

    users = pd.read_csv("data/raw/users.csv", parse_dates=["signup_date"])
    clean_events = pd.read_csv("data/processed/clean_events.csv", parse_dates=["timestamp"])

    funnel_df = compute_funnel(clean_events, users=users)

    activated = set(clean_events.loc[clean_events["event_name"] == "onboarding_completed", "user_id"])
    df = users.copy()
    df["activated"] = df["user_id"].isin(activated)
    control = df[df["experiment_group"] == "control"]
    treatment = df[df["experiment_group"] == "treatment"]
    ab_result = two_proportion_z_test(
        int(control["activated"].sum()), len(control),
        int(treatment["activated"].sum()), len(treatment),
    )

    table = build_initiative_table(funnel_df, ab_result, total_users=len(users))
    print("=== RICE-scored roadmap (ranked) ===")
    print(table[["initiative", "reach", "impact", "confidence", "effort", "rice_score"]].to_string(index=False))
    print("\n=== Confidence basis (why each confidence number is what it is) ===")
    for _, row in table.iterrows():
        print(f"- {row['initiative']}: {row['confidence_basis']}")
