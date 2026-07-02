"""Text embedding via sentence-transformers (all-MiniLM-L6-v2)."""

import logging
from typing import Any, Optional

import numpy as np
from numpy.typing import NDArray
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_MODEL_NAME = "all-MiniLM-L6-v2"
_DIMENSION = 384


def _get_model() -> SentenceTransformer:
    """Load and cache the sentence-transformers model.

    Returns:
        A SentenceTransformer instance.
    """
    return SentenceTransformer(_MODEL_NAME)


def build_job_text(record: dict[str, Any]) -> str:
    """Build a searchable text string from a job record.

    Concatenates title, company, and description for semantic matching.

    Args:
        record: A job record dictionary (from database.crud).

    Returns:
        A formatted string: "{title}. {company}. {description}"
    """
    title = record.get("title", "").strip()
    company = record.get("company", "").strip()
    description = record.get("description", "").strip()
    return f"{title}. {company}. {description}"


def embed(text: str) -> NDArray[np.float32]:
    """Embed a single text string into a 384-dim vector.

    Args:
        text: The input text to embed.

    Returns:
        A numpy array of shape (384,) with float32 values.
    """
    model = _get_model()
    vector = model.encode(text, normalize_embeddings=True)
    return np.array(vector, dtype=np.float32)


def embed_batch(texts: list[str]) -> NDArray[np.float32]:
    """Embed a list of text strings into a matrix of 384-dim vectors.

    Args:
        texts: List of input texts to embed.

    Returns:
        A numpy array of shape (len(texts), 384) with float32 values.
    """
    if not texts:
        return np.empty((0, _DIMENSION), dtype=np.float32)

    model = _get_model()
    vectors = model.encode(texts, normalize_embeddings=True)
    return np.array(vectors, dtype=np.float32)
