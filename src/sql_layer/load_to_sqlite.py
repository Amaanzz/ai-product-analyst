"""
Loads the processed CSV tables into a SQLite database so the SQL analytics
layer (sql/analytics_queries.sql) can be run against a real database rather
than pandas. SQLite is used (stdlib, via Python's sqlite3 module) so this
works with zero extra dependencies -- swap the connection string for
PostgreSQL/DuckDB in a production deployment if preferred.

Run:
    python src/sql_layer/load_to_sqlite.py
"""
import sqlite3
import pandas as pd
import os


def load_to_sqlite(db_path: str = "data/analytics.db",
                    raw_dir: str = "data/raw",
                    processed_dir: str = "data/processed"):
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)

    users = pd.read_csv(f"{raw_dir}/users.csv", parse_dates=["signup_date"])
    clean_events = pd.read_csv(f"{processed_dir}/clean_events.csv", parse_dates=["timestamp"])
    user_features = pd.read_csv(f"{processed_dir}/user_features.csv")
    daily_activity = pd.read_csv(f"{processed_dir}/user_daily_activity.csv")

    users.to_sql("users", conn, if_exists="replace", index=False)
    clean_events.to_sql("events", conn, if_exists="replace", index=False)
    user_features.to_sql("user_features", conn, if_exists="replace", index=False)
    daily_activity.to_sql("user_daily_activity", conn, if_exists="replace", index=False)

    conn.execute("CREATE INDEX idx_events_user_id ON events(user_id)")
    conn.execute("CREATE INDEX idx_events_event_name ON events(event_name)")
    conn.execute("CREATE INDEX idx_users_user_id ON users(user_id)")

    conn.commit()
    print(f"Loaded users, events, user_features, user_daily_activity into {db_path}")
    return conn


if __name__ == "__main__":
    conn = load_to_sqlite()
    conn.close()
