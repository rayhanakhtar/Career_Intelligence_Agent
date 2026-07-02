"""CRUD operations for the jobs table."""

import sqlite3
from typing import Any, Optional


UPSERT_JOB_SQL = """
INSERT INTO jobs (title, company, location, description, apply_url,
                  department, employment_type, posted_at, source, source_id)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(company, title) DO UPDATE SET
    location = excluded.location,
    description = excluded.description,
    apply_url = excluded.apply_url,
    department = excluded.department,
    employment_type = excluded.employment_type,
    posted_at = excluded.posted_at,
    source = excluded.source,
    source_id = excluded.source_id;
"""


SELECT_ALL_SQL = "SELECT * FROM jobs ORDER BY posted_at DESC;"

SELECT_BY_ID_SQL = "SELECT * FROM jobs WHERE id = ?;"

SELECT_COUNT_SQL = "SELECT COUNT(*) FROM jobs;"


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a sqlite3.Row to a dictionary.

    Args:
        row: A row from a SQLite query.

    Returns:
        A dictionary mapping column names to values.
    """
    return dict(row)


def insert_job(conn: sqlite3.Connection, record: dict[str, Any]) -> int:
    """Insert a job record, or update it if a duplicate (company, title) exists.

    Uses UPSERT (ON CONFLICT DO UPDATE) so the original created_at
    is preserved while all other fields are refreshed.

    Args:
        conn: An active SQLite connection.
        record: A dictionary with keys matching the jobs table columns
            (title, company, location, description, apply_url, department,
             employment_type, posted_at, source, source_id).

    Returns:
        The row id of the inserted or updated row.
    """
    cursor = conn.execute(
        UPSERT_JOB_SQL,
        (
            record.get("title", ""),
            record.get("company", ""),
            record.get("location", ""),
            record.get("description", ""),
            record.get("apply_url", ""),
            record.get("department", ""),
            record.get("employment_type", ""),
            record.get("posted_at", ""),
            record.get("source", ""),
            record.get("source_id", ""),
        ),
    )
    conn.commit()
    return cursor.lastrowid or 0


def get_all_jobs(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Retrieve all job records ordered by posted_at descending.

    Args:
        conn: An active SQLite connection.

    Returns:
        A list of job record dictionaries.
    """
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(SELECT_ALL_SQL)
    return [_row_to_dict(row) for row in cursor.fetchall()]


def get_job_by_id(conn: sqlite3.Connection, job_id: int) -> Optional[dict[str, Any]]:
    """Retrieve a single job record by its id.

    Args:
        conn: An active SQLite connection.
        job_id: The primary key id of the job.

    Returns:
        A job record dictionary, or None if not found.
    """
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(SELECT_BY_ID_SQL, (job_id,))
    row = cursor.fetchone()
    return _row_to_dict(row) if row is not None else None


def count_jobs(conn: sqlite3.Connection) -> int:
    """Return the total number of job records.

    Args:
        conn: An active SQLite connection.

    Returns:
        The job count.
    """
    cursor = conn.execute(SELECT_COUNT_SQL)
    return cursor.fetchone()[0]
