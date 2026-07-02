"""Tests for the crawl trigger API endpoint."""

from unittest.mock import patch

from fastapi import status
from fastapi.testclient import TestClient

from api.main import app

_MOCK_GREENHOUSE_JOBS = [
    {
        "title": "AI/ML Intern",
        "company": "testcorp",
        "location": "Bengaluru",
        "description": "ML intern role",
        "apply_url": "https://boards.greenhouse.io/testcorp/jobs/1",
        "department": "Engineering",
        "employment_type": "Internship",
        "posted_at": "2026-07-01",
        "source": "greenhouse",
        "source_id": "1",
    }
]

_MOCK_LEVER_JOBS = [
    {
        "title": "ML Engineer",
        "company": "testlever",
        "location": "Remote",
        "description": "Lever ML role",
        "apply_url": "https://jobs.lever.co/testlever/1",
        "department": "Engineering",
        "employment_type": "Full-time",
        "posted_at": "2026-07-01",
        "source": "lever",
        "source_id": "1",
    }
]


class TestCrawl:
    """Tests for POST /crawl."""

    @patch("api.routes.crawl.fetch_greenhouse_jobs", return_value=_MOCK_GREENHOUSE_JOBS)
    @patch("api.routes.crawl.insert_job")
    def test_crawl_greenhouse_returns_202(self, mock_insert, mock_fetch):
        """POST /crawl with source=greenhouse should return 202."""
        client = TestClient(app)
        response = client.post(
            "/crawl",
            json={"source": "greenhouse", "token": "testcorp"},
        )
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "accepted"

    @patch("api.routes.crawl.fetch_lever_jobs", return_value=_MOCK_LEVER_JOBS)
    @patch("api.routes.crawl.insert_job")
    def test_crawl_lever_returns_202(self, mock_insert, mock_fetch):
        """POST /crawl with source=lever should return 202."""
        client = TestClient(app)
        response = client.post(
            "/crawl",
            json={"source": "lever", "token": "testlever"},
        )
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "accepted"

    def test_crawl_unknown_source_returns_400(self):
        """POST /crawl with an unknown source should return 400."""
        client = TestClient(app)
        response = client.post(
            "/crawl",
            json={"source": "unknown_ats", "token": "test"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "unknown source" in response.json()["detail"].lower()

    def test_crawl_empty_token_returns_400(self):
        """POST /crawl with an empty token should return 400."""
        client = TestClient(app)
        response = client.post(
            "/crawl",
            json={"source": "greenhouse", "token": "   "},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "token" in response.json()["detail"].lower()
