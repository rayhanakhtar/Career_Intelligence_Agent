"""Shared fixtures for API tests."""

import sqlite3
from typing import Any

import pytest

from database.crud import insert_job
from database.schema import create_tables


@pytest.fixture
def sample_jobs() -> list[dict[str, Any]]:
    """Return a list of sample job records for testing."""
    return [
        {
            "title": "AI/ML Engineer Intern",
            "company": "boschglobalsof",
            "location": "Electronic City, Bengaluru",
            "description": "Work on machine learning models and NLP.",
            "apply_url": "https://boards.greenhouse.io/bosch/jobs/1",
            "department": "Engineering",
            "employment_type": "Internship",
            "posted_at": "2026-07-01",
            "source": "greenhouse",
            "source_id": "1",
        },
        {
            "title": "Data Scientist",
            "company": "infosys",
            "location": "Bengaluru",
            "description": "Build data pipelines and dashboards.",
            "apply_url": "https://boards.greenhouse.io/infosys/jobs/2",
            "department": "Data",
            "employment_type": "Full-time",
            "posted_at": "2026-07-02",
            "source": "greenhouse",
            "source_id": "2",
        },
        {
            "title": "Software Engineer",
            "company": "wipro",
            "location": "Electronic City",
            "description": "Develop frontend web applications.",
            "apply_url": "https://boards.greenhouse.io/wipro/jobs/3",
            "department": "Engineering",
            "employment_type": "Full-time",
            "posted_at": "2026-06-30",
            "source": "greenhouse",
            "source_id": "3",
        },
    ]


@pytest.fixture
def db_with_jobs(sample_jobs):
    """Create an in-memory SQLite DB pre-populated with sample jobs."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    create_tables(conn)
    for job in sample_jobs:
        insert_job(conn, job)
    return conn
