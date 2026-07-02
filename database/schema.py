"""SQLite database schema for job storage."""

import sqlite3
from typing import Optional


CREATE_JOBS_TABLE = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT DEFAULT '',
    description TEXT DEFAULT '',
    apply_url TEXT DEFAULT '',
    department TEXT DEFAULT '',
    employment_type TEXT DEFAULT '',
    posted_at TEXT DEFAULT '',
    source TEXT DEFAULT '',
    source_id TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(company, title)
);
"""


def create_tables(conn: sqlite3.Connection) -> None:
    """Create the jobs table if it does not already exist.

    Args:
        conn: An active SQLite connection.
    """
    conn.execute(CREATE_JOBS_TABLE)
    conn.commit()
