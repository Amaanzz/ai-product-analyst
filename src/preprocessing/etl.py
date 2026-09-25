"""
ETL pipeline: raw_events -> clean_events -> user_daily_activity -> user_features

Run after generate_synthetic_data.py:
    python src/preprocessing/etl.py
"""
import os
import pandas as pd


def load_raw(input_dir: str = "data/raw"):
    users = pd.read_csv(f"{input_dir}/users.csv", parse_dates=["signup_date"])
    events = pd.read_csv(f"{input_dir}/events.csv", parse_dates=["timestamp"])
    return users, events


def clean_events(events: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicates, drop rows with missing user_id, drop impossible timestamps.
    This is intentionally simple/explicit rather than clever, so the data-quality
    report (src/quality/data_quality.py) and this cleaning step tell a consistent
    story about what was found and what was done about it."""
    df = events.copy()
    before = len(df)

    df = df.drop_duplicates(subset=["event_id"])
    df = df.dropna(subset=["user_id"])
    # Drop events with implausible timestamps (e.g. far future placeholders)
    df = df[df["timestamp"] < pd.Timestamp("2030-01-01")]
    df = df[df["timestamp"] >= pd.Timestamp("2020-01-01")]

    after = len(df)
    print(f"clean_events: {before} -> {after} rows ({before - after} removed)")
    return df.reset_index(drop=True)


def build_user_daily_activity(clean_events_df: pd.DataFrame) -> pd.DataFrame:
    df = clean_events_df.copy()
    df["date"] = df["timestamp"].dt.date
    daily = (
        df.groupby(["user_id", "date"])
        .agg(
            n_events=("event_id", "count"),
            n_sessions=("session_id", "nunique"),
            ai_events=("event_name", lambda x: (x == "ai_query_submitted").sum()),
        )
        .reset_index()
    )
    return daily


def build_user_features(users: pd.DataFrame, clean_events_df: pd.DataFrame) -> pd.DataFrame:
    df = clean_events_df.copy()

    activated = (
        df[df["event_name"] == "onboarding_completed"]["user_id"].unique()
    )
    ai_adopters = df[df["event_name"] == "ai_assistant_opened"]["user_id"].unique()
    subscribed = df[df["event_name"] == "subscription_started"]["user_id"].unique()

    ai_query_counts = (
        df[df["event_name"] == "ai_query_submitted"]
        .groupby("user_id").size().rename("ai_query_count")
    )
    ai_ratings = (
        df[df["event_name"] == "ai_response_rated"]
        .groupby("user_id").size().rename("ai_rating_count")
    )

    features = users.copy()
    features["activated"] = features["user_id"].isin(activated)
    features["ai_adopter"] = features["user_id"].isin(ai_adopters)
    features["subscribed"] = features["user_id"].isin(subscribed)
    features = features.merge(ai_query_counts, on="user_id", how="left")
    features = features.merge(ai_ratings, on="user_id", how="left")
    features["ai_query_count"] = features["ai_query_count"].fillna(0).astype(int)
    features["ai_rating_count"] = features["ai_rating_count"].fillna(0).astype(int)

    return features


def run_etl(input_dir: str = "data/raw", output_dir: str = "data/processed"):
    os.makedirs(output_dir, exist_ok=True)
    users, events = load_raw(input_dir)

    clean = clean_events(events)
    daily_activity = build_user_daily_activity(clean)
    user_features = build_user_features(users, clean)

    clean.to_csv(f"{output_dir}/clean_events.csv", index=False)
    daily_activity.to_csv(f"{output_dir}/user_daily_activity.csv", index=False)
    user_features.to_csv(f"{output_dir}/user_features.csv", index=False)

    print(f"ETL complete. Wrote clean_events, user_daily_activity, user_features to {output_dir}/")
    return clean, daily_activity, user_features


if __name__ == "__main__":
    run_etl()
