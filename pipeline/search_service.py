"""Shared search service that wraps the ranking pipeline."""

import logging
from typing import Any

from pipeline.rank import rank_jobs

logger = logging.getLogger(__name__)


def search(
    db_path: str,
    resume_text: str,
    top_k: int = 10,
    preferred_locations: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Run the full search pipeline and return ranked results.

    This is the single entry point for both text-search and file-upload
    endpoints. It delegates to ``rank_jobs`` for the actual ranking logic.

    Args:
        db_path: Path to the SQLite database file.
        resume_text: Raw resume text to match against.
        top_k: Number of top results to return.
        preferred_locations: Optional list of location strings to boost.

    Returns:
        A list of job record dictionaries enriched with a ``match_score`` key,
        sorted by descending match score.
    """
    return rank_jobs(
        db_path=db_path,
        resume_text=resume_text,
        top_k=top_k,
        preferred_locations=preferred_locations,
    )
