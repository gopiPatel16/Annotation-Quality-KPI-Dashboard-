"""Load raw CSVs into SQLite and run the named KPI queries."""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def build_db(raw_dir: Path, db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript((ROOT / "sql" / "schema.sql").read_text())
    ann = pd.read_csv(raw_dir / "annotators.csv")
    tasks = pd.read_csv(raw_dir / "tasks.csv")
    tasks["is_gold"] = tasks["is_gold"].astype(int)
    tasks["created_date"] = pd.to_datetime(tasks["created_date"]).dt.strftime("%Y-%m-%d")
    notes = pd.read_csv(raw_dir / "annotations.csv")
    ann.to_sql("annotators", conn, if_exists="append", index=False)
    tasks.to_sql("tasks", conn, if_exists="append", index=False)
    notes.to_sql("annotations", conn, if_exists="append", index=False)
    conn.commit()
    return conn


def load_queries() -> dict[str, str]:
    text = (ROOT / "sql" / "kpi_queries.sql").read_text()
    parts = re.split(r"^-- name:\s*(\w+)\s*$", text, flags=re.M)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}


def run_all(conn: sqlite3.Connection) -> dict[str, pd.DataFrame]:
    return {name: pd.read_sql_query(sql, conn) for name, sql in load_queries().items()}
