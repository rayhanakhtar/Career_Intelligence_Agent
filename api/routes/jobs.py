"""Job listing endpoints: GET /jobs, GET /jobs/{id}."""

import logging
import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_db
from api.models import ErrorResponse, JobResponse
from database.crud import get_all_jobs, get_job_by_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


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


@router.get("", response_model=list[JobResponse])
def list_jobs(conn: sqlite3.Connection = Depends(get_db)):
    """Return all jobs ordered by posted_at descending."""
    jobs = get_all_jobs(conn)
    logger.info("Returning %d jobs", len(jobs))
    return [_row_to_job_response(job) for job in jobs]


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
