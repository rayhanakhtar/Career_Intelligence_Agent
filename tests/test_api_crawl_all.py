"""Tests for the POST /crawl/all and GET /crawl/all/{task_id} endpoints."""

from unittest.mock import patch

from fastapi import status
from fastapi.testclient import TestClient

from api.main import app


class TestCrawlAll:
    """Tests for POST /crawl/all and GET /crawl/all/{task_id}."""

    def test_crawl_all_returns_202(self):
        """POST /crawl/all should return 202 with a task_id."""
        client = TestClient(app)
        response = client.post("/crawl/all")
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "accepted"

    @patch("api.routes.crawl._task_results", {"test-task": {"Co A": 5, "Co B": 3}})
    def test_get_crawl_all_result_completed(self):
        """GET /crawl/all/{task_id} should return results when complete."""
        client = TestClient(app)
        response = client.get("/crawl/all/test-task")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["task_id"] == "test-task"
        assert data["status"] == "completed"
        assert data["results"] == {"Co A": 5, "Co B": 3}

    @patch("api.routes.crawl._task_results", {"running-task": {}})
    def test_get_crawl_all_result_running(self):
        """GET /crawl/all/{task_id} should return status=running when empty."""
        client = TestClient(app)
        response = client.get("/crawl/all/running-task")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["task_id"] == "running-task"
        assert data["status"] == "running"

    def test_get_crawl_all_result_not_found(self):
        """GET /crawl/all/{task_id} should return 404 for unknown task_id."""
        client = TestClient(app)
        response = client.get("/crawl/all/nonexistent-task")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()
