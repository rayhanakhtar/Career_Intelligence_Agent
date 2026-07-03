"""Tests for the crawl trigger API endpoint."""

from unittest.mock import patch

from fastapi import status
from fastapi.testclient import TestClient

from api.main import app


class TestCrawl:
    """Tests for POST /crawl."""

    @patch("api.routes.crawl.get_company")
    def test_crawl_known_company_returns_202(self, mock_get_company):
        """POST /crawl with a valid company_id should return 202."""
        mock_get_company.return_value = {
            "id": "bosch",
            "company": "Bosch",
            "platform": "greenhouse",
            "enabled": True,
        }
        client = TestClient(app)
        response = client.post(
            "/crawl",
            json={"company_id": "bosch"},
        )
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "accepted"

    def test_crawl_unknown_company_returns_400(self):
        """POST /crawl with an unknown company_id should return 400."""
        client = TestClient(app)
        response = client.post(
            "/crawl",
            json={"company_id": "nonexistent_co"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "unknown" in response.json()["detail"].lower()

    @patch("api.routes.crawl.get_company")
    def test_crawl_disabled_company_returns_400(self, mock_get_company):
        """POST /crawl with a disabled company should return 400."""
        mock_get_company.return_value = {
            "id": "disabled_co",
            "company": "Disabled Co",
            "platform": "greenhouse",
            "enabled": False,
        }
        client = TestClient(app)
        response = client.post(
            "/crawl",
            json={"company_id": "disabled_co"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "disabled" in response.json()["detail"].lower()
