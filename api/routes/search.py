"""Resume search endpoint: POST /search (text) and POST /search/upload (file)."""

import logging
import os

from fastapi import APIRouter, File, Form, UploadFile
from fastapi import HTTPException as FastAPIHTTPException
from fastapi import status
from starlette.responses import JSONResponse

from api.extractor import extract_text
from api.models import ErrorResponse, JobWithScore, SearchRequest, SearchResponse
from pipeline.search_service import search as search_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])

DATABASE_PATH = os.getenv("DATABASE_PATH", "jobs.db")


def _run_search(resume_text: str, top_k: int, locations: list[str] | None) -> list[dict]:
    """Internal helper: validate input and delegate to search_service."""
    if not resume_text.strip():
        raise FastAPIHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="resume_text must not be empty",
        )
    top_k = max(1, min(top_k, 100))
    logger.info(
        "Searching top-%d jobs for resume (%d chars), locations=%s",
        top_k,
        len(resume_text),
        locations,
    )
    return search_service(
        db_path=DATABASE_PATH,
        resume_text=resume_text,
        top_k=top_k,
        preferred_locations=locations,
    )


@router.post(
    "",
    response_model=SearchResponse,
    responses={400: {"model": ErrorResponse}},
)
def search_jobs(body: SearchRequest):
    """Rank jobs by semantic similarity to pasted resume text."""
    ranked = _run_search(
        resume_text=body.resume_text,
        top_k=body.top_k,
        locations=body.locations,
    )
    return SearchResponse(results=[JobWithScore(**job) for job in ranked])


@router.post(
    "/upload",
    response_model=SearchResponse,
    responses={400: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def search_jobs_upload(
    resume_file: UploadFile = File(...),
    locations: str = Form(""),
    top_k: int = Form(10),
):
    """Rank jobs by semantic similarity to an uploaded resume file.

    Supports PDF, DOCX, and TXT files. The file is automatically parsed and
    its text content is used for ranking.
    """
    content = await resume_file.read()
    if not content:
        raise FastAPIHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    try:
        resume_text = extract_text(content, resume_file.filename or "resume.txt")
    except ValueError as e:
        raise FastAPIHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if not resume_text.strip():
        raise FastAPIHTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No extractable text found in the uploaded file",
        )

    preferred_locations = (
        [loc.strip() for loc in locations.split(",") if loc.strip()]
        if locations
        else None
    )

    ranked = _run_search(
        resume_text=resume_text,
        top_k=top_k,
        locations=preferred_locations,
    )
    return SearchResponse(results=[JobWithScore(**job) for job in ranked])
