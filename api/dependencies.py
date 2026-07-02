"""FastAPI dependency injection for database connections."""

import os
import sqlite3
from collections.abc import Generator

DATABASE_PATH = os.getenv("DATABASE_PATH", "jobs.db")


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Yield a SQLite connection and close it after the request completes.

    The database path is read from the ``DATABASE_PATH`` environment variable,
    defaulting to ``jobs.db``.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
