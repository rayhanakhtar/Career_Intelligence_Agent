"""Unit tests for the ranking pipeline."""

import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from database.crud import insert_job
from database.schema import create_tables


@pytest.fixture
def db_with_jobs():
    """Create an in-memory SQLite DB with 3 sample jobs and a resume."""
    conn = sqlite3.connect(":memory:")
    create_tables(conn)

    jobs = [
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
    for job in jobs:
        insert_job(conn, job)
    conn.close()
    return jobs


@pytest.fixture
def resume_text():
    return "AI/ML Engineer with experience in Python, PyTorch, and NLP."


# Create 384-dim mock embeddings with predictable similarity rankings.
# Job 0 (bosch AI/ML) should be closest to the resume, Job 2 (wipro frontend) farthest.
_RNG = np.random.default_rng(42)
SAMPLE_EMBEDDINGS = _RNG.normal(size=(3, 384)).astype(np.float32)
SAMPLE_EMBEDDINGS = SAMPLE_EMBEDDINGS / np.linalg.norm(
    SAMPLE_EMBEDDINGS, axis=1, keepdims=True
)
SAMPLE_RESUME_VEC = SAMPLE_EMBEDDINGS[0].copy() + _RNG.normal(
    scale=0.1, size=384
).astype(np.float32)
SAMPLE_RESUME_VEC = SAMPLE_RESUME_VEC / np.linalg.norm(SAMPLE_RESUME_VEC)


class TestRankPipeline:
    """Test suite for the rank pipeline logic."""

    def _make_file_db(self, path, jobs):
        """Create a file-based SQLite DB with sample jobs."""
        conn = sqlite3.connect(path)
        create_tables(conn)
        for job in jobs:
            insert_job(conn, job)
        conn.close()

    @patch("pipeline.rank.embed_batch", return_value=SAMPLE_EMBEDDINGS)
    @patch("pipeline.rank.embed", return_value=SAMPLE_RESUME_VEC)
    def test_rank_returns_top_results(self, mock_embed, mock_embed_batch, tmp_path, db_with_jobs, resume_text):
        """rank_jobs should return ranked results sorted by match_score."""
        db_path = str(tmp_path / "test.db")
        self._make_file_db(db_path, db_with_jobs)

        from pipeline.rank import rank_jobs

        results = rank_jobs(db_path=db_path, resume_text=resume_text, top_k=3)

        assert isinstance(results, list)
        assert len(results) == 3
        assert results[0]["match_score"] >= results[1]["match_score"]
        assert all("match_score" in r for r in results)

    @patch("pipeline.rank.embed_batch", return_value=SAMPLE_EMBEDDINGS)
    @patch("pipeline.rank.embed", return_value=SAMPLE_RESUME_VEC)
    def test_rank_empty_db_returns_empty(self, mock_embed, mock_embed_batch, tmp_path, resume_text):
        """rank_jobs on an empty DB should return an empty list."""
        db_path = str(tmp_path / "empty.db")
        conn = sqlite3.connect(db_path)
        create_tables(conn)
        conn.close()

        from pipeline.rank import rank_jobs

        results = rank_jobs(db_path=db_path, resume_text=resume_text)
        assert results == []

    @patch("pipeline.rank.embed_batch", return_value=SAMPLE_EMBEDDINGS)
    @patch("pipeline.rank.embed", return_value=SAMPLE_RESUME_VEC)
    def test_rank_result_has_expected_keys(self, mock_embed, mock_embed_batch, tmp_path, db_with_jobs, resume_text):
        """Each ranked result should have metadata keys plus match_score."""
        db_path = str(tmp_path / "test.db")
        self._make_file_db(db_path, db_with_jobs)

        from pipeline.rank import rank_jobs

        results = rank_jobs(db_path=db_path, resume_text=resume_text, top_k=1)
        assert len(results) == 1
        r = results[0]
        assert "title" in r
        assert "company" in r
        assert "location" in r
        assert "match_score" in r
        assert isinstance(r["match_score"], float)
