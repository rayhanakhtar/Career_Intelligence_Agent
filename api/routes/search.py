"""Resume search endpoint: POST /search."""

import logging
import os

from fastapi import APIRouter, HTTPException, status

from api.models import ErrorResponse, JobWithScore, SearchRequest, SearchResponse
from pipeline.rank import rank_jobs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])

DATABASE_PATH = os.getenv("DATABASE_PATH", "jobs.db")


@router.post(
    "",
    response_model=SearchResponse,
    responses={400: {"model": ErrorResponse}},
)
def search_jobs(body: SearchRequest):
    """Rank jobs by semantic similarity to the provided resume text."""
    if not body.resume_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="resume_text must not be empty",
        )

    top_k = max(1, min(body.top_k, 100))
    logger.info(
        "Searching top-%d jobs for resume (%d chars)",
        top_k,
        len(body.resume_text),
    )

    ranked = rank_jobs(
        db_path=DATABASE_PATH,
        resume_text=body.resume_text,
        top_k=top_k,
    )

    results = [JobWithScore(**job) for job in ranked]
    return SearchResponse(results=results)
