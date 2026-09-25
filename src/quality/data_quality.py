"""
Data quality report for raw_events.csv.

Checks:
- duplicate event_id
- missing user_id
- invalid/implausible timestamps
- events before the user's signup_date (impossible sequence)

Run:
    python src/quality/data_quality.py
"""
import pandas as pd


def run_quality_report(users_path="data/raw/users.csv", events_path="data/raw/events.csv") -> dict:
    users = pd.read_csv(users_path, parse_dates=["signup_date"])
    events = pd.read_csv(events_path, parse_dates=["timestamp"])

    total_events = len(events)

    n_duplicates = events.duplicated(subset=["event_id"]).sum()
    n_missing_user_id = events["user_id"].isna().sum()
    n_invalid_timestamps = ((events["timestamp"] >= pd.Timestamp("2030-01-01")) |
                             (events["timestamp"] < pd.Timestamp("2020-01-01"))).sum()

    merged = events.merge(users[["user_id", "signup_date"]], on="user_id", how="left")
    n_before_signup = (merged["timestamp"] < merged["signup_date"]).sum()

    report = {
        "total_events": total_events,
        "duplicate_events": n_duplicates,
        "duplicate_events_pct": round(100 * n_duplicates / total_events, 3),
        "missing_user_ids": n_missing_user_id,
        "missing_user_ids_pct": round(100 * n_missing_user_id / total_events, 3),
        "invalid_timestamps": n_invalid_timestamps,
        "invalid_timestamps_pct": round(100 * n_invalid_timestamps / total_events, 3),
        "events_before_signup": int(n_before_signup),
        "events_before_signup_pct": round(100 * n_before_signup / total_events, 3),
    }
    return report


def print_report(report: dict):
    print("=== Data Quality Report ===")
    print(f"Total events:         {report['total_events']:,}")
    print(f"Duplicate events:     {report['duplicate_events']:,} ({report['duplicate_events_pct']}%)")
    print(f"Missing user IDs:     {report['missing_user_ids']:,} ({report['missing_user_ids_pct']}%)")
    print(f"Invalid timestamps:   {report['invalid_timestamps']:,} ({report['invalid_timestamps_pct']}%)")
    print(f"Events before signup: {report['events_before_signup']:,} ({report['events_before_signup_pct']}%)")


if __name__ == "__main__":
    report = run_quality_report()
    print_report(report)
