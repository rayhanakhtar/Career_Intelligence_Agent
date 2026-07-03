"""Crawl trigger endpoint: POST /crawl and POST /crawl/all."""

import logging
import os
import sqlite3
import uuid
from collections.abc import Callable

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from api.models import (
    CrawlAllResponse,
    CrawlAllResultResponse,
    CrawlRequest,
    CrawlResponse,
    ErrorResponse,
)
from crawlers.greenhouse import fetch_jobs as fetch_greenhouse_jobs
from crawlers.lever import fetch_jobs as fetch_lever_jobs
from database.crud import insert_job
from database.schema import create_tables

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/crawl", tags=["crawl"])

DATABASE_PATH = os.getenv("DATABASE_PATH", "jobs.db")

_SOURCE_MAP: dict[str, Callable[..., list[dict]]] = {
    "greenhouse": fetch_greenhouse_jobs,
    "lever": fetch_lever_jobs,
}

# In-memory task-result store (ephemeral — fine for MVP).
_task_results: dict[str, dict[str, int]] = {}


def _run_crawl(source: str, token: str, task_id: str) -> None:
    """Background task: fetch jobs and store them in the database.

    Args:
        source: ATS source name ("greenhouse" or "lever").
        token: Board token (greenhouse) or company slug (lever).
        task_id: Unique identifier for this crawl task.
    """
    fetcher = _SOURCE_MAP.get(source)
    if fetcher is None:
        logger.error("Task %s: unknown source '%s'", task_id, source)
        return

    logger.info("Task %s: crawling %s with token '%s'", task_id, source, token)
    jobs = fetcher(token)

    if not jobs:
        logger.warning("Task %s: no jobs returned for %s/%s", task_id, source, token)
        return

    conn = sqlite3.connect(DATABASE_PATH)
    try:
        create_tables(conn)
        count = 0
        for job in jobs:
            insert_job(conn, job)
            count += 1
        logger.info("Task %s: stored %d jobs from %s/%s", task_id, count, source, token)
    finally:
        conn.close()


def _run_crawl_all(task_id: str) -> None:
    """Background task: run all enabled crawlers via the dispatcher."""
    from crawlers.dispatcher import crawl_all

    logger.info("Task %s: starting crawl-all", task_id)
    results = crawl_all(DATABASE_PATH)
    _task_results[task_id] = results
    logger.info("Task %s: crawl-all complete — %s", task_id, results)


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=CrawlResponse,
    responses={400: {"model": ErrorResponse}},
)
def trigger_crawl(body: CrawlRequest, background_tasks: BackgroundTasks):
    """Trigger a fire-and-forget crawl for a given ATS source and token.

    The crawl runs in the background. Once complete, jobs are written directly
    to the database. There is no task-status tracking in MVP.
    """
    if body.source not in _SOURCE_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown source '{body.source}'. Supported: {list(_SOURCE_MAP.keys())}",
        )

    if not body.token.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="token must not be empty",
        )

    task_id = str(uuid.uuid4())
    background_tasks.add_task(_run_crawl, body.source, body.token, task_id)
    logger.info("Scheduled crawl task %s for %s/%s", task_id, body.source, body.token)

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
