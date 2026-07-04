"""CrawlService — decoupled orchestrator for running crawlers.

Reusable by:
- FastAPI REST endpoints (via background tasks)
- APScheduler (scheduled jobs)
- CLI scripts
"""

import logging
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Any

from crawlers.registry import build_crawlers, get_company, get_crawler_class
from database.crud import insert_job
from database.schema import create_tables

logger = logging.getLogger(__name__)


@dataclass
class CrawlResult:
    """Outcome of crawling a single company."""

    company: str
    platform: str
    status: str  # "success", "no_jobs", "blocked", "failed"
    job_count: int = 0
    error_message: str = ""


@dataclass
class CrawlSummary:
    """Aggregated results of a full crawl run."""

    total_companies: int = 0
    successful: int = 0
    no_jobs: int = 0
    blocked: int = 0
    failed: int = 0
    jobs_by_platform: dict[str, int] = field(default_factory=dict)
    total_jobs: int = 0
    duration_seconds: float = 0.0
    results: list[CrawlResult] = field(default_factory=list)


def _format_summary(summary: CrawlSummary) -> str:
    """Build a human-readable crawl summary block."""
    lines = ["=== Crawl Summary ==="]
    lines.append(f"Companies processed: {summary.total_companies}")
    lines.append(f"  Successful:      {summary.successful}")
    lines.append(f"  No active jobs:  {summary.no_jobs}")
    lines.append(f"  Blocked:         {summary.blocked}")
    lines.append(f"  Failed:          {summary.failed}")
    lines.append("")
    lines.append("Jobs fetched by platform:")
    for platform in sorted(summary.jobs_by_platform):
        lines.append(f"  {platform}: {summary.jobs_by_platform[platform]}")
    lines.append("")
    lines.append(f"Total jobs:       {summary.total_jobs}")
    minutes = int(summary.duration_seconds // 60)
    seconds = int(summary.duration_seconds % 60)
    lines.append(f"Duration:         {minutes}m {seconds}s")
    lines.append("=" * 25)
    return "\n".join(lines)


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

    def crawl_all(self, log_summary: bool = True) -> dict[str, int]:
        """Run every enabled crawler from the registry.

        Args:
            log_summary: Whether to print the aggregated crawl summary.

        Returns:
            A dict mapping company display names to job counts.
        """
        crawlers = build_crawlers()
        if not crawlers:
            logger.warning("No crawlers built from registry — nothing to crawl")
            return {}

        t0 = time.time()
        summary = CrawlSummary(total_companies=len(crawlers))

        for crawler in crawlers:
            result = self._crawl_and_report(crawler)
            summary.results.append(result)

            if result.status == "success":
                summary.successful += 1
                summary.jobs_by_platform[result.platform] = (
                    summary.jobs_by_platform.get(result.platform, 0) + result.job_count
                )
                summary.total_jobs += result.job_count
            elif result.status == "no_jobs":
                summary.no_jobs += 1
            elif result.status == "blocked":
                summary.blocked += 1
            elif result.status == "failed":
                summary.failed += 1

        summary.duration_seconds = time.time() - t0

        if summary.total_jobs > 0:
            self._invalidate_index()

        if log_summary:
            for line in _format_summary(summary).split("\n"):
                logger.info(line)

        return {r.company: r.job_count for r in summary.results if r.job_count > 0}

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
        result = self._crawl_and_report(crawler)
        return result.job_count if result.status == "success" else 0

    def _crawl_and_report(self, crawler: Any) -> CrawlResult:
        """Run a crawler and return a detailed CrawlResult.

        Args:
            crawler: A :class:`BaseCrawler` instance.

        Returns:
            A :class:`CrawlResult` describing the outcome.
        """
        company = crawler.display_name
        platform = getattr(crawler, "platform", "unknown")

        try:
            jobs = crawler.fetch_jobs()
        except Exception as e:
            logger.exception("Crawler failed for '%s'", company)
            return CrawlResult(company=company, platform=platform, status="failed", job_count=0, error_message=str(e))

        if not jobs:
            logger.info("No jobs returned for '%s'", company)
            return CrawlResult(company=company, platform=platform, status="no_jobs", job_count=0)

        conn = sqlite3.connect(self.db_path)
        try:
            create_tables(conn)
            count = 0
            for job in jobs:
                insert_job(conn, job)
                count += 1
            logger.info("Stored %d jobs for '%s'", count, company)
            return CrawlResult(company=company, platform=platform, status="success", job_count=count)
        finally:
            conn.close()
