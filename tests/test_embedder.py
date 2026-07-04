"""Unit tests for the embedding module."""

import numpy as np

from embeddings.embedder import build_job_text, embed, embed_batch

SAMPLE_JOB = {
    "id": 1,
    "title": "AI/ML Engineer Intern",
    "company": "boschglobalsof",
    "location": "Electronic City, Bengaluru",
    "description": "Work on machine learning models and NLP pipelines.",
    "apply_url": "https://boards.greenhouse.io/boschglobalsof/jobs/12345",
    "department": "Engineering",
    "employment_type": "Internship",
    "posted_at": "2026-07-01T12:00:00Z",
    "source": "greenhouse",
    "source_id": "12345",
}


class TestBuildJobText:
    """Test suite for build_job_text()."""

    def test_concatenates_title_company_description(self):
        """build_job_text should produce '{title}. {company}. {description}'."""
        text = build_job_text(SAMPLE_JOB)
        assert text.startswith("AI/ML Engineer Intern. boschglobalsof.")
        assert "Work on machine learning models" in text

    def test_strips_whitespace(self):
        """Whitespace in fields should be stripped."""
        job = {
            "title": "  Engineer  ",
            "company": "  Acme  ",
            "description": "  Do stuff  ",
        }
        text = build_job_text(job)
        assert text == "Engineer. Acme. Do stuff"


class TestEmbed:
    """Test suite for embed()."""

    def test_embed_single_returns_correct_shape(self):
        """embed() should return a 384-dim float32 vector."""
        vector = embed("Machine learning engineer")
        assert isinstance(vector, np.ndarray)
        assert vector.shape == (384,)
        assert vector.dtype == np.float32

    def test_embed_single_is_normalized(self):
        """The returned vector should have unit L2 norm."""
        vector = embed("Data science internship")
        norm = np.linalg.norm(vector)
        assert abs(norm - 1.0) < 1e-5


class TestEmbedBatch:
    """Test suite for embed_batch()."""

    def test_embed_batch_returns_matrix(self):
        """embed_batch() should return a (n, 384) float32 matrix."""
        texts = ["Machine learning", "Data science", "AI intern"]
        matrix = embed_batch(texts)
        assert isinstance(matrix, np.ndarray)
        assert matrix.shape == (3, 384)
        assert matrix.dtype == np.float32

    def test_embed_batch_empty(self):
        """embed_batch([]) should return an empty array."""
        matrix = embed_batch([])
        assert isinstance(matrix, np.ndarray)
        assert matrix.shape == (0, 384)

    def test_embed_batch_rows_are_normalized(self):
        """Each row in the batch output should have unit L2 norm."""
        texts = ["Python developer", "ML researcher"]
        matrix = embed_batch(texts)
        for row in matrix:
            norm = np.linalg.norm(row)
            assert abs(norm - 1.0) < 1e-5
