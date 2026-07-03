"""CrawlService — decoupled orchestrator for running crawlers.

Reusable by:
- FastAPI REST endpoints (via background tasks)
- APScheduler (scheduled jobs)
- CLI scripts
"""

import logging
import sqlite3
from typing import Any

from crawlers.registry import build_crawlers, get_company, get_crawler_class
from database.crud import insert_job
from database.schema import create_tables

logger = logging.getLogger(__name__)


class CrawlService:
    """Decoupled orchestrator that runs crawlers and stores results."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def crawl_one(self, company_id: str) -> int:
        """Crawl a single company by its registry ID.

        Args:
            company_id: The company's ``id`` field in the registry.

        Returns:
            Number of jobs stored, or 0 if the company was not found
            or the crawler failed / is disabled.
        """
        entry = get_company(company_id)
        if entry is None:
            logger.warning("Company '%s' not found in registry", company_id)
            return 0
        if not entry.get("enabled", False):
            logger.info("Company '%s' is disabled — skipping", company_id)
            return 0

        cls = get_crawler_class(entry.get("platform", ""))
        if cls is None:
            logger.warning(
                "No crawler registered for platform '%s' (company '%s')",
                entry.get("platform"),
                entry.get("company"),
            )
            return 0

        crawler = cls.from_registry(entry)
        count = self._crawl_and_store(crawler)
        if count > 0:
            self._invalidate_index()
        return count

    def crawl_all(self) -> dict[str, int]:
        """Run every enabled crawler from the registry.

        Returns:
            A dict mapping company display names to the number of jobs stored.
            Companies that failed or returned zero jobs are omitted.
        """
        crawlers = build_crawlers()
        if not crawlers:
            logger.warning("No crawlers built from registry — nothing to crawl")
            return {}

        summary: dict[str, int] = {}
        for crawler in crawlers:
            count = self._crawl_and_store(crawler)
            if count > 0:
                summary[crawler.display_name] = count
        if summary:
            self._invalidate_index()
        return summary

    def crawl_many(self, company_ids: list[str]) -> dict[str, int]:
        """Crawl a subset of companies by their registry IDs.

        Args:
            company_ids: List of company ``id`` fields.

        Returns:
            A dict mapping company display names to job counts.
        """
        summary: dict[str, int] = {}
        for company_id in company_ids:
            count = self.crawl_one(company_id)
            if count > 0:
                entry = get_company(company_id)
                if entry:
                    summary[entry.get("company", company_id)] = count
        if summary:
            self._invalidate_index()
        return summary

    @staticmethod
    def _invalidate_index() -> None:
        """Invalidate the FAISS index cache so next search picks up new jobs."""
        from pipeline.rank import invalidate_index_cache
        invalidate_index_cache()

    def _crawl_and_store(self, crawler: Any) -> int:
        """Fetch jobs from a crawler and persist them to the database.

        Args:
            crawler: A :class:`BaseCrawler` instance.

        Returns:
            Number of jobs stored, or 0 if the crawler failed.
        """
        company = crawler.display_name
        try:
            jobs = crawler.fetch_jobs()
        except Exception:
            logger.exception("Crawler failed for '%s'", company)
            return 0

        if not jobs:
            logger.info("No jobs returned for '%s'", company)
            return 0

        conn = sqlite3.connect(self.db_path)
        try:
            create_tables(conn)
            count = 0
            for job in jobs:
                insert_job(conn, job)
                count += 1
            logger.info("Stored %d jobs for '%s'", count, company)
            return count
        finally:
            conn.close()
