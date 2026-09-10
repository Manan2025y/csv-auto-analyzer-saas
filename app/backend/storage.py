"""Small local persistence layer for saved dashboards.

This is deliberately provider-neutral: it uses SQLite locally and can later
be replaced by PostgreSQL without changing the UI contract.
"""
from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "csv_auto_analyzer.db"


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS dashboards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        source_file TEXT,
        payload TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")
    conn.commit()
    return conn


def save_dashboard(name: str, source_file: str, payload: dict) -> int:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO dashboards(name, source_file, payload, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (name.strip() or "Untitled dashboard", source_file or "", json.dumps(payload), now, now),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_dashboards():
    with _connect() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM dashboards ORDER BY updated_at DESC")]


def load_dashboard(dashboard_id: int):
    with _connect() as conn:
        row = conn.execute("SELECT * FROM dashboards WHERE id = ?", (dashboard_id,)).fetchone()
        if not row:
            return None
        item = dict(row)
        item["payload"] = json.loads(item["payload"])
        return item


def delete_dashboard(dashboard_id: int):
    with _connect() as conn:
        conn.execute("DELETE FROM dashboards WHERE id = ?", (dashboard_id,))
        conn.commit()
