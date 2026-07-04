"""Tests for the resume search API endpoint."""

from unittest.mock import patch

from fastapi import status
from fastapi.testclient import TestClient

from api.main import app

_FAKE_RANKED = [
    {
        "id": 1,
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
        "created_at": "2026-07-03T00:00:00",
        "match_score": 85.3,
    },
    {
        "id": 2,
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
        "created_at": "2026-07-03T00:00:00",
        "match_score": 62.1,
    },
]


class TestSearch:
    """Tests for POST /search."""

    @patch("api.routes.search.search_service", return_value=_FAKE_RANKED)
    def test_search_returns_ranked_results(self, mock_search):
        """POST /search should return ranked results sorted by match_score."""
        app.dependency_overrides.clear()
        client = TestClient(app)
        response = client.post(
            "/search",
            json={"resume_text": "AI/ML engineer with NLP experience", "top_k": 2},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["results"]) == 2
        assert data["results"][0]["match_score"] == 85.3
        assert data["results"][1]["match_score"] == 62.1
        mock_search.assert_called_once()

    @patch("api.routes.search.search_service", return_value=[])
    def test_search_empty_resume_returns_400(self, mock_search):
        """POST /search with empty resume_text should return 400."""
        client = TestClient(app)
        response = client.post(
            "/search",
            json={"resume_text": "   ", "top_k": 5},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        mock_search.assert_not_called()

    @patch("api.routes.search.search_service", return_value=_FAKE_RANKED)
    def test_search_clamps_top_k(self, mock_search):
        """top_k should be clamped between 1 and 100."""
        app.dependency_overrides.clear()
        client = TestClient(app)
        response = client.post(
            "/search",
            json={"resume_text": "test resume", "top_k": 999},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["results"]) == 2
        mock_search.assert_called_once()
        args, kwargs = mock_search.call_args
        assert kwargs["top_k"] == 100

    @patch("api.routes.search.search_service", return_value=_FAKE_RANKED)
    def test_search_with_locations(self, mock_search):
        """POST /search with locations should pass them through."""
        app.dependency_overrides.clear()
        client = TestClient(app)
        response = client.post(
            "/search",
            json={
                "resume_text": "AI/ML engineer",
                "top_k": 5,
                "locations": ["Bengaluru", "Electronic City"],
            },
        )
        assert response.status_code == status.HTTP_200_OK
        mock_search.assert_called_once()
        args, kwargs = mock_search.call_args
        assert kwargs["preferred_locations"] == ["Bengaluru", "Electronic City"]

    @patch("api.routes.search.search_service", return_value=_FAKE_RANKED)
    def test_search_locations_omitted(self, mock_search):
        """POST /search without locations should pass None."""
        app.dependency_overrides.clear()
        client = TestClient(app)
        response = client.post(
            "/search",
            json={"resume_text": "AI/ML engineer", "top_k": 5},
        )
        assert response.status_code == status.HTTP_200_OK
        mock_search.assert_called_once()
        args, kwargs = mock_search.call_args
        assert kwargs["preferred_locations"] is None


class TestSearchUpload:
    """Tests for POST /search/upload."""

    @patch("api.routes.search.search_service", return_value=_FAKE_RANKED)
    @patch("api.routes.search.extract_text", return_value="Extracted resume text")
    def test_search_upload_txt(self, mock_extract, mock_search):
        """Uploading a TXT file should extract text and return results."""
        client = TestClient(app)
        response = client.post(
            "/search/upload",
            files={"resume_file": ("resume.txt", b"AI/ML engineer", "text/plain")},
            data={"top_k": "2"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["results"]) == 2
        mock_extract.assert_called_once()
        mock_search.assert_called_once()

    @patch("api.routes.search.search_service", return_value=_FAKE_RANKED)
    @patch("api.routes.search.extract_text", return_value="Extracted resume text")
    def test_search_upload_with_locations(self, mock_extract, mock_search):
        """Upload with locations should pass them through."""
        client = TestClient(app)
        response = client.post(
            "/search/upload",
            files={"resume_file": ("resume.txt", b"AI resume", "text/plain")},
            data={"top_k": "5", "locations": "Bengaluru, Electronic City"},
        )
        assert response.status_code == status.HTTP_200_OK
        mock_search.assert_called_once()
        args, kwargs = mock_search.call_args
        assert kwargs["preferred_locations"] == ["Bengaluru", "Electronic City"]

    def test_search_upload_no_file(self):
        """POST /search/upload without a file should return 422."""
        client = TestClient(app)
        response = client.post("/search/upload")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch("api.routes.search.extract_text", side_effect=ValueError("Unsupported file format"))
    def test_search_upload_invalid_format(self, mock_extract):
        """Uploading an unsupported file format should return 400."""
        client = TestClient(app)
        response = client.post(
            "/search/upload",
            files={"resume_file": ("resume.png", b"bad", "image/png")},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Unsupported" in response.json()["detail"]
