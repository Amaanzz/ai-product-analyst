"""
Experiment segmentation: does the AI-assisted onboarding effect hold across
subgroups, or is it concentrated in one segment?

This matters because an overall +9pp lift could be an average masking a much
larger effect in one subgroup and none (or a negative effect) in another --
which changes the rollout recommendation from "ship to everyone" to "ship to
segment X only."

Segments checked: device, acquisition_channel, country. ("New vs existing
user" and "free vs paid" from the original spec are not meaningful subgroup
cuts here -- every synthetic user is new at signup, and plan is an *outcome*
of the funnel, not a pre-existing trait to split on, so splitting the
experiment by it would condition on a post-treatment variable and bias the
comparison. This is a deliberate scope decision, not an oversight.)

Run:
    python src/experimentation/segment_experiment.py
"""
import pandas as pd


def segmented_ab_results(users: pd.DataFrame, clean_events: pd.DataFrame, segment_col: str) -> pd.DataFrame:
    from experimentation.ab_test import two_proportion_z_test  # local import: see __main__ path setup below
    activated_users = set(clean_events.loc[clean_events["event_name"] == "onboarding_completed", "user_id"])
    df = users.copy()
    df["activated"] = df["user_id"].isin(activated_users)

    rows = []
    for segment_value, sub_df in df.groupby(segment_col):
        control = sub_df[sub_df["experiment_group"] == "control"]
        treatment = sub_df[sub_df["experiment_group"] == "treatment"]
        if len(control) < 30 or len(treatment) < 30:
            # Too few users in this cut for a meaningful z-test -- flag rather than
            # silently reporting an unstable p-value from a tiny sample.
            rows.append({
                segment_col: segment_value,
                "n_control": len(control), "n_treatment": len(treatment),
                "note": "sample too small for reliable test (<30 per arm)",
            })
            continue
        result = two_proportion_z_test(
            success_a=int(control["activated"].sum()), n_a=len(control),
            success_b=int(treatment["activated"].sum()), n_b=len(treatment),
        )
        result[segment_col] = segment_value
        rows.append(result)

    return pd.DataFrame(rows)


def summarize_heterogeneity(segmented_df: pd.DataFrame, segment_col: str) -> str:
    """A short, honest read on whether the effect is consistent across the
    segment, or concentrated/reversed in a subgroup -- avoids the common
    mistake of running many subgroup cuts and cherry-picking the one that
    looks most interesting."""
    valid = segmented_df.dropna(subset=["absolute_lift_pp"]) if "absolute_lift_pp" in segmented_df else pd.DataFrame()
    if valid.empty:
        return f"No segment of {segment_col} had enough sample size for a reliable comparison."

    lifts = valid["absolute_lift_pp"]
    all_positive = (lifts > 0).all()
    all_significant = (valid["p_value"] < 0.05).all()
    spread = lifts.max() - lifts.min()

    verdict = f"Across {segment_col} segments, absolute lift ranged from {lifts.min()}pp to {lifts.max()}pp. "
    if all_positive and spread < 10:
        verdict += "The effect direction is consistent and the magnitude doesn't vary dramatically -- no strong evidence the effect is segment-specific."
    elif not all_positive:
        verdict += "At least one segment shows a lift in the opposite direction -- this warrants investigation before a blanket rollout recommendation."
    else:
        verdict += f"The {spread:.1f}pp spread across segments suggests the effect may be stronger in some segments than others -- worth considering a targeted rather than blanket rollout."
    if not all_significant:
        verdict += " Not every segment reached statistical significance individually, which is expected with smaller per-segment sample sizes and doesn't by itself mean the effect disappears there."
    return verdict


if __name__ == "__main__":
    import sys
    sys.path.append("src")
    users = pd.read_csv("data/raw/users.csv", parse_dates=["signup_date"])
    clean_events = pd.read_csv("data/processed/clean_events.csv", parse_dates=["timestamp"])

    for segment_col in ["device", "acquisition_channel", "country"]:
        print(f"\n=== A/B lift by {segment_col} ===")
        seg_results = segmented_ab_results(users, clean_events, segment_col)
        print(seg_results.to_string(index=False))
        print(f"\n-- Heterogeneity check ({segment_col}) --")
        print(summarize_heterogeneity(seg_results, segment_col))
