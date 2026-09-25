"""
Synthetic data generator for InsightAI (fictional product).

IMPORTANT: All data produced here is synthetic. It is designed to be *plausible*
(consistent with typical SaaS product behaviour) but does not represent any real
company, product, or user. This is deliberate and disclosed in the README.

Design choices baked in (so the rest of the pipeline has real signal to find):
- Users who complete onboarding are more likely to retain (activation -> retention link)
- Users assigned to the "treatment" experiment group (AI-assisted onboarding) have a
  higher activation rate than "control" -- this is the ground-truth effect the A/B
  test module should recover statistically.
- AI feature usage is correlated with retention, but we deliberately do NOT make it
  a perfectly clean causal signal -- some retained users never touch the AI feature,
  and some AI-heavy users still churn. Real product data is never this clean, and the
  analysis modules must not pretend otherwise (see README methodological rule).
- A small number of data quality issues (duplicate events, missing user_id, bad
  timestamps) are deliberately injected so the data-quality module has something to
  catch and report on.

Run:
    python src/ingestion/generate_synthetic_data.py --n-users 5000 --seed 42
"""
import argparse
import random
import uuid
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

COUNTRIES = ["US", "UK", "IN", "DE", "BR", "CA", "AU"]
DEVICES = ["desktop", "mobile", "tablet"]
CHANNELS = ["organic", "paid_search", "referral", "social", "content"]
PLANS = ["free", "pro", "enterprise"]
AGE_GROUPS = ["18-24", "25-34", "35-44", "45-54", "55+"]

FUNNEL_EVENTS = [
    "signup",
    "onboarding_started",
    "onboarding_completed",
    "project_created",
    "document_uploaded",
    "ai_assistant_opened",
    "ai_query_submitted",
    "ai_response_received",
    "ai_response_rated",
    "output_saved",
]
OTHER_EVENTS = ["collaboration_invited", "subscription_started", "subscription_cancelled"]


def generate_users(n_users: int, start_date: datetime, days: int, rng: np.random.Generator) -> pd.DataFrame:
    signup_offsets = rng.integers(0, days, size=n_users)
    signup_dates = [start_date + timedelta(days=int(o)) for o in signup_offsets]

    # Experiment assignment: 50/50 control vs treatment (AI-assisted onboarding)
    experiment_group = rng.choice(["control", "treatment"], size=n_users, p=[0.5, 0.5])

    users = pd.DataFrame({
        "user_id": [str(uuid.uuid4()) for _ in range(n_users)],
        "signup_date": signup_dates,
        "country": rng.choice(COUNTRIES, size=n_users, p=[0.30, 0.15, 0.15, 0.10, 0.10, 0.10, 0.10]),
        "device": rng.choice(DEVICES, size=n_users, p=[0.55, 0.35, 0.10]),
        "acquisition_channel": rng.choice(CHANNELS, size=n_users, p=[0.35, 0.25, 0.15, 0.15, 0.10]),
        "age_group": rng.choice(AGE_GROUPS, size=n_users),
        "experiment_group": experiment_group,
    })
    return users


def simulate_user_journey(user_row, rng: np.random.Generator):
    """Simulate one user's event sequence, with baked-in behavioural effects."""
    events = []
    t = pd.Timestamp(user_row["signup_date"]) + timedelta(minutes=int(rng.integers(0, 60)))
    session_id = str(uuid.uuid4())

    def emit(event_name, ts, feature=None):
        events.append({
            "event_id": str(uuid.uuid4()),
            "user_id": user_row["user_id"],
            "timestamp": ts,
            "event_name": event_name,
            "session_id": session_id,
            "platform": user_row["device"],
            "feature": feature,
            "experiment_group": user_row["experiment_group"],
        })

    emit("signup", t)

    # Onboarding: treatment group (AI-assisted onboarding) gets a real activation lift.
    p_start_onboarding = 0.85
    base_completion = 0.62
    treatment_lift = 0.09 if user_row["experiment_group"] == "treatment" else 0.0
    p_complete_onboarding = min(base_completion + treatment_lift, 0.95)

    if rng.random() > p_start_onboarding:
        return events  # dropped before onboarding even started
    t += timedelta(minutes=int(rng.integers(1, 30)))
    emit("onboarding_started", t)

    if rng.random() > p_complete_onboarding:
        return events  # dropped mid-onboarding
    t += timedelta(minutes=int(rng.integers(2, 45)))
    emit("onboarding_completed", t)

    # Activated users proceed further, with declining probability at each stage
    if rng.random() < 0.80:
        t += timedelta(hours=int(rng.integers(0, 6)))
        emit("project_created", t)

        if rng.random() < 0.65:
            t += timedelta(hours=int(rng.integers(0, 12)))
            emit("document_uploaded", t)

        if rng.random() < 0.55:
            t += timedelta(hours=int(rng.integers(0, 6)))
            emit("ai_assistant_opened", t, feature="ai_assistant")

            n_queries = rng.poisson(3) + 1
            for _ in range(min(n_queries, 8)):
                t += timedelta(minutes=int(rng.integers(1, 20)))
                emit("ai_query_submitted", t, feature="ai_assistant")
                t += timedelta(seconds=int(rng.integers(2, 15)))
                emit("ai_response_received", t, feature="ai_assistant")
                if rng.random() < 0.4:
                    emit("ai_response_rated", t, feature="ai_assistant")

            if rng.random() < 0.5:
                t += timedelta(minutes=int(rng.integers(1, 30)))
                emit("output_saved", t)

    if rng.random() < 0.08:
        emit("collaboration_invited", t + timedelta(days=int(rng.integers(1, 10))))

    # Subscription: correlated with activation depth (proxy: number of events so far)
    activation_depth = len(events)
    p_subscribe = 0.05 + 0.02 * min(activation_depth, 10)
    if rng.random() < p_subscribe:
        emit("subscription_started", t + timedelta(days=int(rng.integers(1, 14))))
        if rng.random() < 0.1:
            emit("subscription_cancelled", t + timedelta(days=int(rng.integers(15, 60))))

    return events


def simulate_retention_activity(user_id, activated, ai_adopter, experiment_group, signup_date,
                                 observation_days, rng: np.random.Generator):
    """Generate sparse return-visit events over subsequent weeks, to support
    D1/D7/D30 retention calculations. Retention probability depends on activation
    and AI adoption, but noisily -- not a clean deterministic function."""
    events = []
    base_p = 0.15
    if activated:
        base_p += 0.25
    if ai_adopter:
        base_p += 0.15
    base_p = min(base_p, 0.85)

    for day in range(1, observation_days):
        if rng.random() < base_p * (0.97 ** day):  # decays over time
            ts = pd.Timestamp(signup_date) + timedelta(days=day, hours=int(rng.integers(8, 22)))
            events.append({
                "event_id": str(uuid.uuid4()),
                "user_id": user_id,
                "timestamp": ts,
                "event_name": "ai_query_submitted" if (ai_adopter and rng.random() < 0.6) else "app_opened",
                "session_id": str(uuid.uuid4()),
                "platform": None,
                "feature": "ai_assistant" if ai_adopter else None,
                "experiment_group": experiment_group,
            })
    return events


def inject_data_quality_issues(events_df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Deliberately introduce a small, known set of data quality issues so the
    data-quality module (src/quality/data_quality.py) has real things to catch."""
    df = events_df.copy()
    n = len(df)

    # 1. Duplicate ~0.3% of events
    n_dupes = int(n * 0.003)
    dupes = df.sample(n=n_dupes, random_state=1)
    df = pd.concat([df, dupes], ignore_index=True)

    # 2. Null out user_id on ~0.08% of rows
    idx = rng.choice(df.index, size=max(1, int(len(df) * 0.0008)), replace=False)
    df.loc[idx, "user_id"] = None

    # 3. Corrupt ~0.02% of timestamps (set to far-future / far-past)
    idx = rng.choice(df.index, size=max(1, int(len(df) * 0.0002)), replace=False)
    df.loc[idx, "timestamp"] = pd.Timestamp("2099-01-01")

    return df


def main(n_users: int, seed: int, observation_days: int, output_dir: str):
    rng = np.random.default_rng(seed)
    random.seed(seed)
    start_date = datetime(2025, 1, 1)

    users = generate_users(n_users, start_date, days=120, rng=rng)

    all_events = []
    for _, row in users.iterrows():
        journey = simulate_user_journey(row, rng)
        all_events.extend(journey)

        activated = any(e["event_name"] == "onboarding_completed" for e in journey)
        ai_adopter = any(e["event_name"] == "ai_assistant_opened" for e in journey)
        retention_events = simulate_retention_activity(
            row["user_id"], activated, ai_adopter, row["experiment_group"],
            row["signup_date"], observation_days, rng,
        )
        all_events.extend(retention_events)

    events_df = pd.DataFrame(all_events)
    events_df = inject_data_quality_issues(events_df, rng)

    # Assign plan post-hoc: users with a subscription_started event get "pro", rest "free"
    subscribed_users = set(events_df.loc[events_df["event_name"] == "subscription_started", "user_id"])
    users["plan"] = users["user_id"].apply(lambda u: "pro" if u in subscribed_users else "free")

    import os
    os.makedirs(output_dir, exist_ok=True)
    users.to_csv(f"{output_dir}/users.csv", index=False)
    events_df.to_csv(f"{output_dir}/events.csv", index=False)

    print(f"Generated {len(users)} users and {len(events_df)} events.")
    print(f"Saved to {output_dir}/users.csv and {output_dir}/events.csv")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic InsightAI event data")
    parser.add_argument("--n-users", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--observation-days", type=int, default=45)
    parser.add_argument("--output-dir", type=str, default="data/raw")
    args = parser.parse_args()
    main(args.n_users, args.seed, args.observation_days, args.output_dir)
