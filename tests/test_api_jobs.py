"""Tests for the job listing API endpoints."""

from fastapi import status
from fastapi.testclient import TestClient

from api.dependencies import get_db
from api.main import app


def _override_get_db(db_with_jobs):
    """Create a dependency override function bound to the given connection."""
    def _get_db_override():
        yield db_with_jobs
    return _get_db_override


class TestListJobs:
    """Tests for GET /jobs."""

    def test_list_jobs_empty(self):
        """GET /jobs on an empty database should return an empty list."""
        app.dependency_overrides.clear()
        import sqlite3
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        from database.schema import create_tables
        create_tables(conn)

        app.dependency_overrides[get_db] = _override_get_db(conn)
        client = TestClient(app)
        response = client.get("/jobs")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []
        conn.close()

    def test_list_jobs_with_data(self, db_with_jobs):
        """GET /jobs should return all jobs."""
        app.dependency_overrides[get_db] = _override_get_db(db_with_jobs)
        client = TestClient(app)
        response = client.get("/jobs")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 3
        assert data[0]["title"] == "Data Scientist"
        assert data[1]["title"] == "AI/ML Engineer Intern"
        assert data[2]["title"] == "Software Engineer"

    def test_list_jobs_response_shape(self, db_with_jobs):
        """Each job response should have the expected fields."""
        app.dependency_overrides[get_db] = _override_get_db(db_with_jobs)
        client = TestClient(app)
        response = client.get("/jobs")
        data = response.json()[0]
        expected_keys = {
            "id", "title", "company", "location", "description",
            "apply_url", "department", "employment_type", "posted_at",
            "source", "source_id", "created_at",
        }
        assert set(data.keys()) == expected_keys


class TestGetJob:
    """Tests for GET /jobs/{id}."""

    def test_get_job_found(self, db_with_jobs):
        """GET /jobs/1 should return the first job."""
        app.dependency_overrides[get_db] = _override_get_db(db_with_jobs)
        client = TestClient(app)
        response = client.get("/jobs/1")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == 1
        assert data["title"] == "AI/ML Engineer Intern"
        assert data["company"] == "boschglobalsof"

    def test_get_job_not_found(self, db_with_jobs):
        """GET /jobs/999 should return 404."""
        app.dependency_overrides[get_db] = _override_get_db(db_with_jobs)
        client = TestClient(app)
        response = client.get("/jobs/999")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()
