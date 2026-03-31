"""
SQLite storage for collected call-center stats.
"""
import sqlite3
import datetime
from pathlib import Path


def get_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS samples (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            ts           TEXT NOT NULL,          -- ISO-8601 timestamp (local time)
            day_of_week  INTEGER NOT NULL,       -- 0=Monday … 6=Sunday
            hour         INTEGER NOT NULL,       -- 0-23
            minute       INTEGER NOT NULL,       -- 0-59
            calls        INTEGER,               -- שיחות פעילות
            waiting      INTEGER,               -- פונים ממתינים
            connected    INTEGER,               -- מתנדבים מחוברים
            on_break     INTEGER                -- מתנדבים בהפסקה
        )
    """)
    conn.commit()


def insert_sample(conn: sqlite3.Connection, data: dict) -> None:
    now = datetime.datetime.now()
    conn.execute(
        """INSERT INTO samples
               (ts, day_of_week, hour, minute, calls, waiting, connected, on_break)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            now.isoformat(timespec="seconds"),
            now.weekday(),
            now.hour,
            now.minute,
            data.get("calls"),
            data.get("waiting"),
            data.get("connected"),
            data.get("on_break"),
        ),
    )
    conn.commit()


def fetch_all(conn: sqlite3.Connection) -> list:
    cur = conn.execute("SELECT * FROM samples ORDER BY ts")
    return [dict(row) for row in cur.fetchall()]


def fetch_recent_days(conn: sqlite3.Connection, days: int = 7) -> list:
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat(
        timespec="seconds"
    )
    cur = conn.execute(
        "SELECT * FROM samples WHERE ts >= ? ORDER BY ts", (cutoff,)
    )
    return [dict(row) for row in cur.fetchall()]
