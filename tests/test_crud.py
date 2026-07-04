"""Unit tests for the database CRUD module."""

import sqlite3

import pytest

from database.crud import count_jobs, get_all_jobs, get_job_by_id, insert_job
from database.schema import create_tables

SAMPLE_RECORD = {
    "title": "AI/ML Engineer Intern",
    "company": "boschglobalsof",
    "location": "Electronic City, Bengaluru",
    "description": "Work on machine learning models",
    "apply_url": "https://boards.greenhouse.io/boschglobalsof/jobs/12345",
    "department": "Engineering",
    "employment_type": "Internship",
    "posted_at": "2026-07-01T12:00:00Z",
    "source": "greenhouse",
    "source_id": "12345",
}


@pytest.fixture
def db_conn():
    """Create an in-memory SQLite database with the jobs table."""
    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    yield conn
    conn.close()


class TestInsertJob:
    """Test suite for insert_job()."""

    def test_insert_returns_positive_id(self, db_conn):
        """Inserting a job should return a positive row id."""
        job_id = insert_job(db_conn, SAMPLE_RECORD)
        assert job_id > 0

    def test_insert_and_retrieve(self, db_conn):
        """An inserted job should be retrievable by its id."""
        job_id = insert_job(db_conn, SAMPLE_RECORD)
        job = get_job_by_id(db_conn, job_id)
        assert job is not None
        assert job["title"] == "AI/ML Engineer Intern"
        assert job["company"] == "boschglobalsof"
        assert job["location"] == "Electronic City, Bengaluru"
        assert job["source"] == "greenhouse"

    def test_insert_same_company_title_updates(self, db_conn):
        """Inserting the same (company, title) should UPSERT, not duplicate."""
        insert_job(db_conn, SAMPLE_RECORD)
        assert count_jobs(db_conn) == 1

        updated = {**SAMPLE_RECORD, "location": "New Location"}
        insert_job(db_conn, updated)
        assert count_jobs(db_conn) == 1

        job = get_job_by_id(db_conn, 1)
        assert job is not None
        assert job["location"] == "New Location"

    def test_insert_multiple_records(self, db_conn):
        """Inserting different (company, title) pairs should create separate rows."""
        record_b = {**SAMPLE_RECORD, "company": "infosys", "source_id": "67890"}
        insert_job(db_conn, SAMPLE_RECORD)
        insert_job(db_conn, record_b)
        assert count_jobs(db_conn) == 2


class TestGetAllJobs:
    """Test suite for get_all_jobs()."""

    def test_get_all_empty(self, db_conn):
        """An empty table should return an empty list."""
        jobs = get_all_jobs(db_conn)
        assert jobs == []

    def test_get_all_returns_all(self, db_conn):
        """get_all_jobs should return all inserted records."""
        insert_job(db_conn, SAMPLE_RECORD)
        record_b = {**SAMPLE_RECORD, "company": "infosys", "source_id": "67890"}
        record_c = {**SAMPLE_RECORD, "company": "wipro", "source_id": "11111"}
        insert_job(db_conn, record_b)
        insert_job(db_conn, record_c)
        jobs = get_all_jobs(db_conn)
        assert len(jobs) == 3

    def test_get_all_returns_dicts(self, db_conn):
        """Each returned item should be a dictionary with expected keys."""
        insert_job(db_conn, SAMPLE_RECORD)
        jobs = get_all_jobs(db_conn)
        job = jobs[0]
        assert isinstance(job, dict)
        assert "title" in job
        assert "company" in job
        assert "location" in job
        assert "id" in job
        assert "created_at" in job


class TestGetJobById:
    """Test suite for get_job_by_id()."""

    def test_get_nonexistent_returns_none(self, db_conn):
        """Looking up a non-existent id should return None."""
        job = get_job_by_id(db_conn, 999)
        assert job is None

    def test_get_by_id_returns_correct_job(self, db_conn):
        """get_job_by_id should return the correct job record."""
        insert_job(db_conn, SAMPLE_RECORD)
        record_b = {**SAMPLE_RECORD, "company": "infosys", "source_id": "67890"}
        insert_job(db_conn, record_b)
        job = get_job_by_id(db_conn, 2)
        assert job is not None
        assert job["company"] == "infosys"
