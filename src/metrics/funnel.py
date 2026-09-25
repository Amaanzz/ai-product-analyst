"""
Funnel analysis: signup -> onboarding_started -> onboarding_completed ->
project_created -> ai_assistant_opened -> output_saved

Run:
    python src/metrics/funnel.py
"""
import pandas as pd

FUNNEL_STAGES = [
    "signup",
    "onboarding_started",
    "onboarding_completed",
    "project_created",
    "ai_assistant_opened",
    "output_saved",
]


def compute_funnel(clean_events: pd.DataFrame, users: pd.DataFrame = None,
                    stages=FUNNEL_STAGES, segment_col: str = None) -> pd.DataFrame:
    """Returns a DataFrame with one row per stage: users_reached, conversion_from_previous,
    conversion_from_start. If segment_col is given, computes the funnel per segment value.

    IMPORTANT: `users` (the canonical users table) is used as the starting population
    for the 'signup' stage, not the signup *event*. A small number of users can lose
    their signup event during ETL cleaning (e.g. deduplication catching a corrupted
    row) while still being valid, assigned users -- using the event count as the
    signup denominator silently undercounts the true population. All downstream
    stages still come from clean_events as before.
    """

    def _funnel_for(df, start_users=None):
        users_per_stage = []
        for stage in stages:
            if stage == "signup" and start_users is not None:
                users_at_stage = set(start_users["user_id"])
            else:
                users_at_stage = set(df.loc[df["event_name"] == stage, "user_id"])
            users_per_stage.append(users_at_stage)

        rows = []
        start_count = len(users_per_stage[0]) if users_per_stage else 0
        prev_count = None
        for stage, users_set in zip(stages, users_per_stage):
            count = len(users_set)
            conv_from_prev = round(100 * count / prev_count, 2) if prev_count else 100.0
            conv_from_start = round(100 * count / start_count, 2) if start_count else 0.0
            rows.append({
                "stage": stage,
                "users_reached": count,
                "conversion_from_previous_pct": conv_from_prev,
                "conversion_from_start_pct": conv_from_start,
            })
            prev_count = count
        return pd.DataFrame(rows)

    if segment_col is None:
        return _funnel_for(clean_events, start_users=users)

    results = []
    if users is not None and segment_col in users.columns:
        for segment_value, sub_events in clean_events.groupby(segment_col):
            sub_users = users[users[segment_col] == segment_value]
            f = _funnel_for(sub_events, start_users=sub_users)
            f[segment_col] = segment_value
            results.append(f)
    else:
        for segment_value, sub_df in clean_events.groupby(segment_col):
            f = _funnel_for(sub_df)
            f[segment_col] = segment_value
            results.append(f)
    return pd.concat(results, ignore_index=True)


if __name__ == "__main__":
    clean_events = pd.read_csv("data/processed/clean_events.csv", parse_dates=["timestamp"])
    users = pd.read_csv("data/raw/users.csv")

    print("=== Overall funnel ===")
    print(compute_funnel(clean_events, users=users).to_string(index=False))

    print("\n=== Funnel by experiment_group ===")
    print(compute_funnel(clean_events, users=users, segment_col="experiment_group").to_string(index=False))
