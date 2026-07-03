"""Crawl trigger endpoint: POST /crawl and POST /crawl/all."""

import logging
import os
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from api.models import (
    CrawlAllResponse,
    CrawlAllResultResponse,
    CrawlRequest,
    CrawlResponse,
    ErrorResponse,
)
from crawlers.registry import get_company
from crawlers.service import CrawlService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/crawl", tags=["crawl"])

DATABASE_PATH = os.getenv("DATABASE_PATH", "jobs.db")

# In-memory task-result store (ephemeral — fine for MVP).
_task_results: dict[str, dict[str, int]] = {}


def _run_crawl(company_id: str, task_id: str) -> None:
    """Background task: crawl a single company and store jobs.

    Args:
        company_id: The company's ``id`` field in the registry.
        task_id: Unique identifier for this crawl task.
    """
    service = CrawlService(DATABASE_PATH)
    count = service.crawl_one(company_id)
    logger.info("Task %s: crawl of '%s' complete — %d jobs stored", task_id, company_id, count)


def _run_crawl_all(task_id: str) -> None:
    """Background task: run all enabled crawlers via CrawlService."""
    service = CrawlService(DATABASE_PATH)

    logger.info("Task %s: starting crawl-all", task_id)
    results = service.crawl_all()
    _task_results[task_id] = results
    logger.info("Task %s: crawl-all complete — %s", task_id, results)


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=CrawlResponse,
    responses={400: {"model": ErrorResponse}},
)
def trigger_crawl(body: CrawlRequest, background_tasks: BackgroundTasks):
    """Trigger a fire-and-forget crawl for a single company from the registry.

    The crawl runs in the background. The company must exist in the registry
    and be enabled.
    """
    company = get_company(body.company_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown company_id '{body.company_id}'. Check the registry.",
        )
    if not company.get("enabled", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Company '{body.company_id}' is disabled in the registry.",
        )

    task_id = str(uuid.uuid4())
    background_tasks.add_task(_run_crawl, body.company_id, task_id)
    logger.info("Scheduled crawl task %s for company '%s'", task_id, body.company_id)

    return CrawlResponse(task_id=task_id, status="accepted")


@router.post(
    "/all",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=CrawlAllResponse,
)
def trigger_crawl_all(background_tasks: BackgroundTasks):
    """Trigger a fire-and-forget crawl of all enabled companies in the registry.

    Returns immediately with a ``task_id``. The caller can poll
    ``GET /crawl/all/{task_id}`` for per-company results.
    """
    task_id = str(uuid.uuid4())
    _task_results[task_id] = {}
    background_tasks.add_task(_run_crawl_all, task_id)
    logger.info("Scheduled crawl-all task %s", task_id)
    return CrawlAllResponse(task_id=task_id, status="accepted")


@router.get(
    "/all/{task_id}",
    response_model=CrawlAllResultResponse,
)
def get_crawl_all_result(task_id: str):
    """Poll the result of a previous ``POST /crawl/all``.

    Returns the per-company job counts once the crawl is complete, or a
    ``status`` of ``"running"`` if the background task has not finished yet.
    """
    results = _task_results.get(task_id)
    if results is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found",
        )
    if not results:
        return CrawlAllResultResponse(task_id=task_id, status="running", results={})
    return CrawlAllResultResponse(task_id=task_id, status="completed", results=results)
