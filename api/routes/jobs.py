"""Job listing endpoints: GET /jobs, GET /jobs/{id}."""

import logging
import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import get_db
from api.models import ErrorResponse, JobResponse, PaginatedJobsResponse
from database.crud import get_job_by_id, get_jobs_filtered

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])

_DEFAULT_PER_PAGE = 50
_MAX_PER_PAGE = 100


def _row_to_job_response(job: dict[str, Any]) -> JobResponse:
    """Convert a job dict from CRUD into a validated JobResponse."""
    return JobResponse(
        id=job["id"],
        title=job["title"],
        company=job["company"],
        location=job["location"],
        description=job["description"],
        apply_url=job["apply_url"],
        department=job["department"],
        employment_type=job["employment_type"],
        posted_at=job["posted_at"],
        source=job["source"],
        source_id=job["source_id"],
        created_at=job.get("created_at", ""),
    )


@router.get("", response_model=PaginatedJobsResponse)
def list_jobs(
    conn: sqlite3.Connection = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(_DEFAULT_PER_PAGE, ge=1, le=_MAX_PER_PAGE, description="Results per page"),
    company: str | None = Query(None, description="Filter by company name (substring)"),
    location: str | None = Query(None, description="Filter by location (substring)"),
    source: str | None = Query(None, description="Filter by source (exact, e.g. greenhouse)"),
):
    """Return paginated jobs with optional filtering."""
    jobs, total = get_jobs_filtered(
        conn,
        page=page,
        per_page=per_page,
        company=company,
        location=location,
        source=source,
    )
    logger.info(
        "Returning %d jobs (page %d, %d per page, %d total matching filters)",
        len(jobs),
        page,
        per_page,
        total,
    )
    return PaginatedJobsResponse(
        items=[_row_to_job_response(job) for job in jobs],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_job(job_id: int, conn: sqlite3.Connection = Depends(get_db)):
    """Return a single job by its id."""
    job = get_job_by_id(conn, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with id {job_id} not found",
        )
    return _row_to_job_response(job)
