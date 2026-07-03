"""Orchestrator that runs all enabled crawlers and stores results."""

import logging
import sqlite3
from typing import Any

from crawlers.registry import build_crawlers
from database.crud import insert_job
from database.schema import create_tables

logger = logging.getLogger(__name__)


def crawl_all(db_path: str) -> dict[str, int]:
    """Run every enabled crawler from the registry and store jobs in the DB.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        A dict mapping company display names to the number of jobs stored.
        Companies that failed or returned zero jobs are omitted.
    """
    crawlers = build_crawlers()
    if not crawlers:
        logger.warning("No crawlers built from registry — nothing to crawl")
        return {}

    conn = sqlite3.connect(db_path)
    try:
        create_tables(conn)
        summary: dict[str, int] = {}

        for crawler in crawlers:
            company = crawler.display_name
            try:
                jobs = crawler.fetch_jobs()
            except Exception:
                logger.exception("Crawler failed for '%s'", company)
                continue

            if not jobs:
                logger.info("No jobs returned for '%s'", company)
                continue

            count = 0
            for job in jobs:
                insert_job(conn, job)
                count += 1
            summary[company] = count
            logger.info("Stored %d jobs for '%s'", count, company)

        return summary
    finally:
        conn.close()
