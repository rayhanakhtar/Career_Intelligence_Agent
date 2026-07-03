"""Tests for the shared search service."""

from unittest.mock import patch

from pipeline.search_service import search


class TestSearchService:
    """Tests for pipeline.search_service.search()."""

    @patch("pipeline.search_service.rank_jobs")
    def test_search_passes_all_args(self, mock_rank_jobs):
        """search() should delegate to rank_jobs with correct args."""
        mock_rank_jobs.return_value = [{"id": 1, "match_score": 85.0}]

        results = search(
            db_path="test.db",
            resume_text="AI/ML engineer resume",
            top_k=5,
            preferred_locations=["Bengaluru"],
        )

        mock_rank_jobs.assert_called_once_with(
            db_path="test.db",
            resume_text="AI/ML engineer resume",
            top_k=5,
            preferred_locations=["Bengaluru"],
        )
        assert results == [{"id": 1, "match_score": 85.0}]

    @patch("pipeline.search_service.rank_jobs")
    def test_search_without_locations(self, mock_rank_jobs):
        """search() should pass None for locations when not provided."""
        mock_rank_jobs.return_value = []

        search(
            db_path="test.db",
            resume_text="test",
            top_k=3,
        )

        mock_rank_jobs.assert_called_once_with(
            db_path="test.db",
            resume_text="test",
            top_k=3,
            preferred_locations=None,
        )

    @patch("pipeline.search_service.rank_jobs")
    def test_search_returns_empty_from_empty_db(self, mock_rank_jobs):
        """search() should propagate empty results."""
        mock_rank_jobs.return_value = []

        results = search(db_path="test.db", resume_text="test")
        assert results == []
