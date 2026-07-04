"""Crawler for Ashby ATS via the official public Job Posting API."""

import json
import logging
import time
from typing import Any

from crawlers.base import BaseCrawler
from crawlers.utils import get_with_retry

logger = logging.getLogger(__name__)

ASHBY_API_BASE = "https://api.ashbyhq.com/posting-api/job-board/{board}"


def _build_job_record(raw: dict[str, Any], company_name: str) -> dict[str, Any]:
    """Normalise a raw Ashby job dict into the standard job record format."""
    employment_type_map = {
        "FullTime": "Full-time",
        "PartTime": "Part-time",
        "Intern": "Intern",
        "Contract": "Contract",
        "Temporary": "Temporary",
    }
    raw_emp_type = raw.get("employmentType") or ""
    employment_type = employment_type_map.get(raw_emp_type, raw_emp_type)

    workplace_type = raw.get("workplaceType") or ""
    location = raw.get("location") or ""
    if workplace_type:
        location = f"{location} ({workplace_type})" if location else workplace_type

    description = raw.get("descriptionPlain") or raw.get("descriptionHtml") or ""

    return {
        "title": raw.get("title") or "",
        "company": company_name,
        "location": location,
        "description": description,
        "apply_url": raw.get("applyUrl") or raw.get("jobUrl") or "",
        "department": raw.get("department") or raw.get("team") or "",
        "employment_type": employment_type,
        "posted_at": raw.get("publishedAt") or "",
        "source": "ashby",
        "source_id": raw.get("id") or raw.get("jobUrl") or "",
    }


def fetch_jobs(board_token: str) -> list[dict[str, Any]]:
    """Fetch all active jobs from an Ashby job board.

    Args:
        board_token: The Ashby board slug (e.g. "sarvam" for jobs.ashbyhq.com/sarvam).

    Returns:
        A list of standardised job record dictionaries.
    """
    url = ASHBY_API_BASE.format(board=board_token)
    t0 = time.time()
    response = get_with_retry(url)
    elapsed = time.time() - t0

    if response is None:
        logger.error("Failed to fetch jobs for Ashby board '%s' (%.2fs)", board_token, elapsed)
        return []

    try:
        data = response.json()
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Invalid JSON from Ashby API for '%s': %s (%.2fs)", board_token, e, elapsed)
        return []

    raw_jobs = data.get("jobs", [])
    if not isinstance(raw_jobs, list):
        logger.warning("Unexpected response format from Ashby API for '%s' (%.2fs)", board_token, elapsed)
        return []

    listed = [j for j in raw_jobs if j.get("isListed", True)]
    logger.info("Fetched %d jobs from Ashby board '%s' (%.2fs)", len(listed), board_token, elapsed)
    return [_build_job_record(job, board_token) for job in listed]


class AshbyCrawler(BaseCrawler):
    """Crawler for a specific company's Ashby ATS board."""

    platform = "ashby"

    def __init__(
        self,
        company_id: str,
        display_name: str,
        board_token: str,
        locations: list[str] | None = None,
    ) -> None:
        super().__init__(company_id, display_name, locations)
        self.board_token = board_token

    def fetch_jobs(self) -> list[dict[str, Any]]:
        raw_jobs = fetch_jobs(self.board_token)
        return [{**job, "company": self.display_name} for job in raw_jobs]

    @classmethod
    def from_registry(cls, entry: dict[str, Any]) -> "AshbyCrawler":
        return cls(
            company_id=entry["id"],
            display_name=entry["company"],
            board_token=entry["board_token"],
            locations=entry.get("locations", []),
        )
