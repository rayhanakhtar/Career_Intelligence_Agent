"""Unit tests for the FAISS vector store module."""

import os
import tempfile

import numpy as np
import pytest

from embeddings.vector_store import FAISSVectorStore


@pytest.fixture
def sample_data():
    """Create 10 random 384-dim normalised vectors with ids 1–10."""
    rng = np.random.default_rng(42)
    vectors = rng.normal(size=(10, 384)).astype(np.float32)
    # L2 normalise
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors = vectors / norms
    ids = list(range(1, 11))
    return vectors, ids


class TestBuild:
    """Test suite for building the FAISS index."""

    def test_build_with_data(self, sample_data):
        """Building with data should populate the index."""
        vectors, ids = sample_data
        store = FAISSVectorStore()
        store.build(vectors, ids)
        assert store.index is not None
        assert store.index.ntotal == 10

    def test_build_empty(self):
        """Building with empty data should not crash."""
        store = FAISSVectorStore()
        store.build(np.empty((0, 384), dtype=np.float32), [])
        assert store.index is not None
        assert store.index.ntotal == 0

    def test_build_mismatched_counts_raises(self):
        """Mismatched embeddings/ids should raise ValueError."""
        store = FAISSVectorStore()
        vectors = np.zeros((5, 384), dtype=np.float32)
        with pytest.raises(ValueError):
            store.build(vectors, [1, 2, 3])


class TestSearch:
    """Test suite for searching the FAISS index."""

    def test_search_returns_top_k(self, sample_data):
        """Searching should return the requested number of results."""
        vectors, ids = sample_data
        store = FAISSVectorStore()
        store.build(vectors, ids)

        query = vectors[0]
        results = store.search(query, k=3)
        assert len(results) == 3

    def test_search_top_result_is_self(self, sample_data):
        """The top result should be the query vector itself (score ~1.0)."""
        vectors, ids = sample_data
        store = FAISSVectorStore()
        store.build(vectors, ids)

        query = vectors[0]
        results = store.search(query, k=1)
        assert len(results) == 1
        job_id, score = results[0]
        assert job_id == ids[0]
        assert abs(score - 1.0) < 1e-3

    def test_search_empty_index_returns_empty(self):
        """Searching an empty index should return an empty list."""
        store = FAISSVectorStore()
        store.build(np.empty((0, 384), dtype=np.float32), [])
        results = store.search(np.zeros(384, dtype=np.float32), k=5)
        assert results == []

    def test_search_unbuilt_raises(self):
        """Searching before build() should raise RuntimeError."""
        store = FAISSVectorStore()
        with pytest.raises(RuntimeError):
            store.search(np.zeros(384, dtype=np.float32), k=5)


class TestSaveLoad:
    """Test suite for saving and loading the FAISS index."""

    def test_save_and_load(self, sample_data):
        """Saved index should load with the same data."""
        vectors, ids = sample_data
        store = FAISSVectorStore()
        store.build(vectors, ids)

        with tempfile.TemporaryDirectory() as tmpdir:
            store.save(tmpdir)
            assert os.path.exists(os.path.join(tmpdir, "index.faiss"))
            assert os.path.exists(os.path.join(tmpdir, "id_map.npy"))

            loaded = FAISSVectorStore()
            loaded.load(tmpdir)
            assert loaded.index is not None
            assert loaded.index.ntotal == 10
            assert loaded.id_map == ids

    def test_save_unbuilt_raises(self):
        """Saving before build() should raise RuntimeError."""
        store = FAISSVectorStore()
        with pytest.raises(RuntimeError):
            store.save("/tmp/nowhere")

    def test_load_nonexistent_raises(self):
        """Loading from a non-existent path should raise FileNotFoundError."""
        store = FAISSVectorStore()
        with pytest.raises(FileNotFoundError):
            store.load("/tmp/nonexistent_index")
