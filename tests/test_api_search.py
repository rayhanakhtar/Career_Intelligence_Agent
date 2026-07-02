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

    @patch("api.routes.search.rank_jobs", return_value=_FAKE_RANKED)
    def test_search_returns_ranked_results(self, mock_rank):
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
        mock_rank.assert_called_once()

    @patch("api.routes.search.rank_jobs", return_value=[])
    def test_search_empty_resume_returns_400(self, mock_rank):
        """POST /search with empty resume_text should return 400."""
        client = TestClient(app)
        response = client.post(
            "/search",
            json={"resume_text": "   ", "top_k": 5},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        mock_rank.assert_not_called()

    @patch("api.routes.search.rank_jobs", return_value=_FAKE_RANKED)
    def test_search_clamps_top_k(self, mock_rank):
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
        mock_rank.assert_called_once()
        args, kwargs = mock_rank.call_args
        assert kwargs["top_k"] == 100
