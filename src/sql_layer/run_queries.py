"""
Runs every query in sql/analytics_queries.sql against the SQLite database
and prints results -- used both as a sanity check (does every query actually
execute and return sensible rows?) and as a way to demo the SQL layer without
needing a SQL client installed.

Run:
    python src/sql_layer/load_to_sqlite.py   # (re)build the DB first
    python src/sql_layer/run_queries.py
"""
import sqlite3
import re


def split_queries(sql_text: str):
    """Split the .sql file into individual numbered queries (each starts with
    a '-- N. LABEL' comment line) and return (label, sql) pairs."""
    parts = re.split(r"\n(?=-- \d+\. )", sql_text)
    queries = []
    for part in parts:
        m = re.match(r"--\s*(\d+\.\s*[^\n]+)", part.strip())
        if not m:
            continue
        label = m.group(1).strip()
        queries.append((label, part.strip()))
    return queries


def run_all(db_path="data/analytics.db", sql_path="sql/analytics_queries.sql"):
    with open(sql_path) as f:
        sql_text = f.read()

    queries = split_queries(sql_text)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    for label, query_sql in queries:
        print(f"\n=== {label} ===")
        try:
            cur = conn.execute(query_sql)
            rows = cur.fetchall()
            if not rows:
                print("(no rows returned)")
                continue
            cols = rows[0].keys()
            print(" | ".join(cols))
            for row in rows[:15]:
                print(" | ".join(str(row[c]) for c in cols))
            if len(rows) > 15:
                print(f"... ({len(rows)} rows total)")
        except Exception as e:
            print(f"ERROR running query: {e}")

    conn.close()


if __name__ == "__main__":
    run_all()
