"""FAISS vector index for fast nearest-neighbor search."""

import logging
import os

import faiss
import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)


class FAISSVectorStore:
    """A FAISS index wrapper using IndexFlatIP (cosine similarity).

    Vectors are assumed to be L2-normalised already (as produced by
    embedder.py), so inner product equals cosine similarity.

    Attributes:
        index: The underlying FAISS index (None until build() or load()).
        id_map: List mapping index position → job id (None until build()).
        dimension: Embedding dimension (384 for all-MiniLM-L6-v2).
    """

    def __init__(self):
        self.index: faiss.Index | None = None
        self.id_map: list[int] = []
        self.dimension: int = 0

    def build(self, embeddings: NDArray[np.float32], ids: list[int]) -> None:
        """Build a FAISS index from a matrix of embeddings.

        Args:
            embeddings: Numpy array of shape (n_jobs, dimension), float32.
            ids: List of integer job ids corresponding to each row.

        Raises:
            ValueError: If the number of embeddings does not match the number of ids.
        """
        if len(embeddings) != len(ids):
            raise ValueError(f"Embeddings count ({len(embeddings)}) must match ids count ({len(ids)})")
        if len(embeddings) == 0:
            logger.warning("Building FAISS index with zero vectors")
            self.dimension = self.dimension or 384
            self.index = faiss.IndexFlatIP(self.dimension)
            self.id_map = []
            return

        self.dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(embeddings)
        self.id_map = ids[:]
        logger.info("Built FAISS index with %d vectors (dim=%d)", len(ids), self.dimension)

    def save(self, path: str) -> None:
        """Save the FAISS index and id map to disk.

        Args:
            path: Directory path to save files (will be created if missing).
        """
        if self.index is None:
            raise RuntimeError("Cannot save: index has not been built yet")

        os.makedirs(path, exist_ok=True)
        faiss.write_index(self.index, os.path.join(path, "index.faiss"))

        id_map_path = os.path.join(path, "id_map.npy")
        np.save(id_map_path, np.array(self.id_map, dtype=np.int64))
        logger.info("Saved FAISS index to %s (%d vectors)", path, len(self.id_map))

    def load(self, path: str) -> None:
        """Load a FAISS index and id map from disk.

        Args:
            path: Directory path containing index.faiss and id_map.npy.
        """
        index_path = os.path.join(path, "index.faiss")
        id_map_path = os.path.join(path, "id_map.npy")

        if not os.path.exists(index_path) or not os.path.exists(id_map_path):
            raise FileNotFoundError(f"FAISS index files not found in {path}. Expected {index_path} and {id_map_path}")

        self.index = faiss.read_index(index_path)
        self.id_map = list(np.load(id_map_path))
        logger.info(
            "Loaded FAISS index from %s (%d vectors, dim=%d)",
            path,
            len(self.id_map),
            self.index.d,
        )

    def search(self, query_vector: NDArray[np.float32], k: int = 10) -> list[tuple[int, float]]:
        """Search for the k nearest neighbours of a query vector.

        Args:
            query_vector: A single 384-dim query vector, shape (384,) or (1, 384).
            k: Number of nearest neighbours to return.

        Returns:
            A list of (job_id, score) tuples, sorted by descending score.
        """
        if self.index is None:
            raise RuntimeError("Cannot search: index has not been built yet")

        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)

        if self.index.ntotal == 0:
            return []

        distances, indices = self.index.search(query_vector, k)

        results: list[tuple[int, float]] = []
        for dist, idx in zip(distances[0], indices[0], strict=True):
            if idx == -1:
                continue
            job_id = self.id_map[idx]
            score = float(dist)
            results.append((job_id, score))

        return results
