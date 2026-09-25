import pandas as pd


def generate_recommendations(funnel_df: pd.DataFrame, ab_result: dict,
                              ai_adoption: dict, business_impact: dict,
                              heterogeneity_note: str = None) -> list:
    """Returns a list of recommendation dicts. Rules are evaluated
    independently -- more than one can fire."""
    recs = []

    # --- Rule 1: funnel drop-off ---
    funnel_sorted = funnel_df.sort_values("users_reached", ascending=False).reset_index(drop=True)
    biggest_drop = funnel_df.loc[funnel_df["conversion_from_previous_pct"].idxmin()] \
        if funnel_df["conversion_from_previous_pct"].notna().any() else None

    if biggest_drop is not None and biggest_drop["conversion_from_previous_pct"] < 60:
        conversion_pct = float(biggest_drop["conversion_from_previous_pct"])

        recs.append({
            "trigger": (
                f"Stage '{biggest_drop['stage']}' retains only "
                f"{conversion_pct:.2f}% of the previous stage"
            ),
            "recommendation": (
                f"Investigate and improve the '{biggest_drop['stage']}' step -- "
                f"it is the single largest drop-off point in the funnel"
            ),
            "evidence": {
                "stage": biggest_drop["stage"],
                "conversion_from_previous_pct": conversion_pct,
            },
            "confidence": "High" if conversion_pct < 50 else "Medium",
        })

    # --- Rule 2: A/B experiment result ---
    if ab_result.get("p_value", 1) < 0.05 and ab_result.get("absolute_lift_pp", 0) > 0:
        ci_low, ci_high = ab_result.get("ci_95_absolute_lift_pp", (None, None))

        # Convert NumPy scalar values to ordinary Python floats
        # so they display cleanly in the dashboard/API.
        ci_low = float(ci_low) if ci_low is not None else None
        ci_high = float(ci_high) if ci_high is not None else None

        ci_excludes_zero = (
            ci_low is not None
            and ci_high is not None
            and (ci_low > 0 or ci_high < 0)
        )

        confidence = "High" if ci_excludes_zero else "Medium"

        rec_text = (
            "Roll out AI-assisted onboarding to all new users -- the randomised "
            "experiment shows a statistically significant activation lift"
        )

        if heterogeneity_note and "opposite direction" in heterogeneity_note:
            rec_text += (
                ". Caveat: the effect was not uniform across all subgroups checked "
                "(see experiment segmentation) -- consider a targeted rollout or "
                "further investigation before a blanket launch"
            )
            confidence = "Medium"

        # Convert all numeric evidence to ordinary Python floats.
        evidence = {}

        for key in [
            "control_rate_pct",
            "treatment_rate_pct",
            "absolute_lift_pp",
            "p_value",
            "cohens_h",
        ]:
            if key in ab_result:
                value = ab_result[key]
                evidence[key] = float(value) if value is not None else None

        recs.append({
            "trigger": (
                f"A/B test: {float(ab_result['absolute_lift_pp']):.2f}pp lift, "
                f"p={float(ab_result['p_value']):.3g}, "
                f"95% CI [{ci_low:.2f}, {ci_high:.2f}] pp"
            ),
            "recommendation": rec_text,
            "evidence": evidence,
            "confidence": confidence,
        })

    elif ab_result.get("p_value", 1) >= 0.05:
        p_value = ab_result.get("p_value")
        absolute_lift = ab_result.get("absolute_lift_pp")

        recs.append({
            "trigger": (
                f"A/B test did not reach significance "
                f"(p={float(p_value):.3g})"
                if p_value is not None
                else "A/B test did not reach significance"
            ),
            "recommendation": (
                "Do not roll out yet -- either extend the experiment to gather "
                "more data, or conclude the treatment has no meaningful effect"
            ),
            "evidence": {
                "p_value": float(p_value) if p_value is not None else None,
                "absolute_lift_pp": (
                    float(absolute_lift)
                    if absolute_lift is not None
                    else None
                ),
            },
            "confidence": "Medium",
        })

    # --- Rule 3: AI adoption + cost justification ---
    adoption_pct = float(ai_adoption.get("ai_adoption_pct", 0))
    roi_pct = business_impact.get("roi_pct")

    if roi_pct is not None:
        roi_pct = float(roi_pct)

    if adoption_pct > 20 and roi_pct is not None and roi_pct > 0:
        recs.append({
            "trigger": (
                f"AI adoption at {adoption_pct:.2f}% "
                f"with positive ROI ({roi_pct:.1f}%)"
            ),
            "recommendation": (
                "Continue investing in the AI feature -- usage is meaningful "
                "and current revenue comfortably covers AI cost"
            ),
            "evidence": {
                "ai_adoption_pct": adoption_pct,
                "roi_pct": roi_pct,
            },
            "confidence": "Medium",
            # ROI relies on the disclosed ARPU/cost-per-query assumptions.
        })

    elif adoption_pct <= 20:
        recs.append({
            "trigger": f"AI adoption is only {adoption_pct:.2f}%",
            "recommendation": (
                "Investigate AI feature discoverability -- low adoption limits "
                "how much value the feature can create regardless of its quality"
            ),
            "evidence": {
                "ai_adoption_pct": adoption_pct,
            },
            "confidence": "Medium",
        })

    return recs


def recommendations_to_dataframe(recs: list) -> pd.DataFrame:
    return pd.DataFrame(recs)


if __name__ == "__main__":
    import sys
    sys.path.append("src")

    from metrics.funnel import compute_funnel
    from experimentation.ab_test import two_proportion_z_test
    from experimentation.segment_experiment import (
        segmented_ab_results,
        summarize_heterogeneity,
    )
    from ai_analysis.ai_feature_metrics import compute_adoption, compute_cost
    from business_impact.roi import compute_business_impact

    users = pd.read_csv(
        "data/raw/users.csv",
        parse_dates=["signup_date"],
    )

    clean_events = pd.read_csv(
        "data/processed/clean_events.csv",
        parse_dates=["timestamp"],
    )

    user_features = pd.read_csv(
        "data/processed/user_features.csv"
    )

    funnel_df = compute_funnel(clean_events, users=users)

    activated = set(
        clean_events.loc[
            clean_events["event_name"] == "onboarding_completed",
            "user_id",
        ]
    )

    df = users.copy()
    df["activated"] = df["user_id"].isin(activated)

    control = df[df["experiment_group"] == "control"]
    treatment = df[df["experiment_group"] == "treatment"]

    ab_result = two_proportion_z_test(
        int(control["activated"].sum()),
        len(control),
        int(treatment["activated"].sum()),
        len(treatment),
    )

    seg = segmented_ab_results(
        users,
        clean_events,
        "device",
    )

    heterogeneity_note = summarize_heterogeneity(
        seg,
        "device",
    )

    adoption = compute_adoption(user_features)
    ai_cost = compute_cost(clean_events, user_features)
    impact = compute_business_impact(user_features, ai_cost)

    recs = generate_recommendations(
        funnel_df,
        ab_result,
        adoption,
        impact,
        heterogeneity_note,
    )

    print("=== Recommendations ===")

    for r in recs:
        print(f"\n[{r['confidence']} confidence] {r['recommendation']}")
        print(f"  Trigger: {r['trigger']}")
        print(f"  Evidence: {r['evidence']}")