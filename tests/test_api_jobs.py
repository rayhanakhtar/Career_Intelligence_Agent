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
        """GET /jobs on an empty database should return an empty page."""
        app.dependency_overrides.clear()
        import sqlite3

        conn = sqlite3.connect(":memory:", check_same_thread=False)
        from database.schema import create_tables

        create_tables(conn)

        app.dependency_overrides[get_db] = _override_get_db(conn)
        client = TestClient(app)
        response = client.get("/jobs")
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["items"] == []
        assert body["total"] == 0
        assert body["page"] == 1
        conn.close()

    def test_list_jobs_with_data(self, db_with_jobs):
        """GET /jobs should return all jobs."""
        app.dependency_overrides[get_db] = _override_get_db(db_with_jobs)
        client = TestClient(app)
        response = client.get("/jobs")
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert len(body["items"]) == 3
        assert body["total"] == 3
        assert body["page"] == 1

    def test_list_jobs_response_shape(self, db_with_jobs):
        """Each job response should have the expected fields."""
        app.dependency_overrides[get_db] = _override_get_db(db_with_jobs)
        client = TestClient(app)
        response = client.get("/jobs")
        item = response.json()["items"][0]
        expected_keys = {
            "id",
            "title",
            "company",
            "location",
            "description",
            "apply_url",
            "department",
            "employment_type",
            "posted_at",
            "source",
            "source_id",
            "created_at",
        }
        assert set(item.keys()) == expected_keys

    def test_list_jobs_pagination(self, db_with_jobs):
        """GET /jobs?page=1&per_page=2 should paginate correctly."""
        app.dependency_overrides[get_db] = _override_get_db(db_with_jobs)
        client = TestClient(app)
        response = client.get("/jobs?page=1&per_page=2")
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert len(body["items"]) == 2
        assert body["total"] == 3
        assert body["page"] == 1
        assert body["per_page"] == 2

    def test_list_jobs_filters(self, db_with_jobs):
        """GET /jobs?company=infosys should filter correctly."""
        app.dependency_overrides[get_db] = _override_get_db(db_with_jobs)
        client = TestClient(app)
        response = client.get("/jobs?company=infosys")
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert len(body["items"]) == 1
        assert body["items"][0]["company"] == "infosys"
        assert body["total"] == 1


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
