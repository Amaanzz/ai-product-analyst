"""
Retention & cohort analysis.

IMPORTANT: All findings here are OBSERVATIONAL ASSOCIATIONS, not causal claims.
E.g. "AI adopters retain better" does not mean "AI adoption causes retention" --
see README methodological rule. Only src/experimentation/ab_test.py supports
causal language, because it uses randomised assignment.

Run:
    python src/metrics/retention.py
"""
import pandas as pd


def compute_day_n_retention(clean_events: pd.DataFrame, users: pd.DataFrame, day: int) -> float:
    """Fraction of users with at least one event on exactly day N after signup."""
    df = clean_events.merge(users[["user_id", "signup_date"]], on="user_id", how="left")
    df["days_since_signup"] = (df["timestamp"].dt.normalize() - df["signup_date"].dt.normalize()).dt.days
    active_on_day = set(df.loc[df["days_since_signup"] == day, "user_id"])
    return round(100 * len(active_on_day) / users["user_id"].nunique(), 2)


def compute_retention_curve(clean_events: pd.DataFrame, users: pd.DataFrame, days=(1, 7, 14, 30)) -> pd.DataFrame:
    rows = [{"day": d, "retention_pct": compute_day_n_retention(clean_events, users, d)} for d in days]
    return pd.DataFrame(rows)


def compute_cohort_retention(clean_events: pd.DataFrame, users: pd.DataFrame) -> pd.DataFrame:
    """Signup-month cohorts x weeks-since-signup retention matrix."""
    df = clean_events.merge(users[["user_id", "signup_date"]], on="user_id", how="left")
    df["cohort_month"] = df["signup_date"].dt.to_period("M").astype(str)
    df["weeks_since_signup"] = ((df["timestamp"] - df["signup_date"]).dt.days // 7)

    cohort_sizes = users.copy()
    cohort_sizes["cohort_month"] = cohort_sizes["signup_date"].dt.to_period("M").astype(str)
    cohort_sizes = cohort_sizes.groupby("cohort_month")["user_id"].nunique().rename("cohort_size")

    active = (
        df[df["weeks_since_signup"] >= 0]
        .groupby(["cohort_month", "weeks_since_signup"])["user_id"]
        .nunique()
        .reset_index(name="active_users")
    )
    active = active.merge(cohort_sizes, on="cohort_month")
    active["retention_pct"] = round(100 * active["active_users"] / active["cohort_size"], 2)
    return active.sort_values(["cohort_month", "weeks_since_signup"])


def compute_behavioural_cohort_comparison(user_features: pd.DataFrame, clean_events: pd.DataFrame,
                                           users: pd.DataFrame, day: int = 30) -> pd.DataFrame:
    """Compare D-day retention between behavioural cohorts: AI adopters vs not,
    activated vs not. Explicitly labelled as association, not causation."""
    retention_flags = []
    df = clean_events.merge(users[["user_id", "signup_date"]], on="user_id", how="left")
    df["days_since_signup"] = (df["timestamp"].dt.normalize() - df["signup_date"].dt.normalize()).dt.days
    retained_on_day = set(df.loc[df["days_since_signup"] == day, "user_id"])

    uf = user_features.copy()
    uf["retained_day_n"] = uf["user_id"].isin(retained_on_day)

    rows = []
    for col in ["ai_adopter", "activated"]:
        for val in [True, False]:
            subset = uf[uf[col] == val]
            if len(subset) == 0:
                continue
            rows.append({
                "cohort": f"{col}={val}",
                "n_users": len(subset),
                f"retention_day_{day}_pct": round(100 * subset["retained_day_n"].mean(), 2),
                "note": "observational association, not causal",
            })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    users = pd.read_csv("data/raw/users.csv", parse_dates=["signup_date"])
    clean_events = pd.read_csv("data/processed/clean_events.csv", parse_dates=["timestamp"])
    user_features = pd.read_csv("data/processed/user_features.csv")

    print("=== Overall retention curve ===")
    print(compute_retention_curve(clean_events, users).to_string(index=False))

    print("\n=== Behavioural cohort comparison (D30) ===")
    print(compute_behavioural_cohort_comparison(user_features, clean_events, users, day=30).to_string(index=False))
