"""Crawl trigger endpoint: POST /crawl (fire-and-forget)."""

import logging
import os
import sqlite3
import uuid
from collections.abc import Callable

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from api.models import CrawlRequest, CrawlResponse, ErrorResponse
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
