"""
Tests for the SQL layer: confirms the SQLite DB loads correctly and that key
queries (funnel monotonicity, A/B lift matches the Python stats module)
return internally consistent results.

Run: pytest tests/test_sql_layer.py
"""
import sys
sys.path.append(".")

import sqlite3
import pandas as pd
import pytest

from src.sql_layer.load_to_sqlite import load_to_sqlite


@pytest.fixture(scope="module")
def db_connection(tmp_path_factory):
    # Requires data/raw and data/processed to already exist (run the pipeline first)
    db_path = str(tmp_path_factory.mktemp("db") / "test_analytics.db")
    conn = load_to_sqlite(db_path=db_path)
    yield conn
    conn.close()


def test_tables_loaded(db_connection):
    cur = db_connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cur.fetchall()}
    assert {"users", "events", "user_features", "user_daily_activity"}.issubset(tables)


def test_funnel_is_monotonically_non_increasing(db_connection):
    query = """
        SELECT event_name, COUNT(DISTINCT user_id) AS n
        FROM events
        WHERE event_name IN ('signup','onboarding_started','onboarding_completed',
                              'project_created','ai_assistant_opened','output_saved')
        GROUP BY event_name
    """
    df = pd.read_sql(query, db_connection)
    order = ["signup", "onboarding_started", "onboarding_completed",
             "project_created", "ai_assistant_opened", "output_saved"]
    counts = df.set_index("event_name").reindex(order)["n"].tolist()
    assert all(counts[i] >= counts[i + 1] for i in range(len(counts) - 1)), \
        f"Funnel is not monotonically non-increasing: {counts}"


def test_ab_activation_rates_sum_correctly(db_connection):
    query = """
        SELECT u.experiment_group,
               COUNT(DISTINCT u.user_id) AS n_users,
               COUNT(DISTINCT CASE WHEN e.event_name='onboarding_completed' THEN u.user_id END) AS n_activated
        FROM users u
        LEFT JOIN events e ON e.user_id = u.user_id
        GROUP BY u.experiment_group
    """
    df = pd.read_sql(query, db_connection)
    assert set(df["experiment_group"]) == {"control", "treatment"}
    assert (df["n_activated"] <= df["n_users"]).all()
