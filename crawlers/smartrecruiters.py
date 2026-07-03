"""Crawler for SmartRecruiters ATS via the public Posting API."""

import json
import logging
import time
from typing import Any

from crawlers.base import BaseCrawler
from crawlers.utils import get_with_retry

logger = logging.getLogger(__name__)

SMARTRECRUITERS_API_BASE = "https://api.smartrecruiters.com/v1/companies/{company}/postings"
_PAGE_SIZE = 100


def _build_job_record(raw: dict[str, Any], company_name: str) -> dict[str, Any]:
    """Normalise a raw SmartRecruiters job dict into the standard job record format."""
    location = raw.get("location") or {}
    location_parts = [
        location.get("city") or "",
        location.get("region") or "",
        location.get("country") or "",
    ]
    location_str = ", ".join(p for p in location_parts if p)

    return {
        "title": raw.get("name") or "",
        "company": company_name,
        "location": location_str,
        "description": "",
        "apply_url": raw.get("ref") or "",
        "department": (raw.get("department") or {}).get("label") or "",
        "employment_type": (raw.get("type") or {}).get("label") or "",
        "posted_at": raw.get("releasedDate") or "",
        "source": "smartrecruiters",
        "source_id": raw.get("uuid") or raw.get("id") or "",
    }


def fetch_jobs(company_token: str) -> list[dict[str, Any]]:
    """Fetch all active jobs from a SmartRecruiters company feed.

    Args:
        company_token: The company identifier (e.g. "FractalAnalytics"
            from careers.smartrecruiters.com/FractalAnalytics).

    Returns:
        A list of standardised job record dictionaries.
    """
    url = SMARTRECRUITERS_API_BASE.format(company=company_token)
    all_jobs: list[dict[str, Any]] = []
    offset = 0
    t0 = time.time()

    while True:
        page_url = f"{url}?limit={_PAGE_SIZE}&offset={offset}"
        response = get_with_retry(page_url)

        if response is None:
            logger.error("Failed to fetch SmartRecruiters page at offset %d for '%s'", offset, company_token)
            break

        try:
            data = response.json()
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("Invalid JSON from SmartRecruiters API for '%s': %s", company_token, e)
            break

        content = data.get("content", [])
        all_jobs.extend(content)

        total = data.get("totalFound", 0)
        if offset + len(content) >= total:
            break

        offset += len(content)

    elapsed = time.time() - t0
    logger.info("Fetched %d jobs from SmartRecruiters company '%s' (%.2fs)", len(all_jobs), company_token, elapsed)
    return [_build_job_record(job, company_token) for job in all_jobs]


class SmartRecruitersCrawler(BaseCrawler):
    """Crawler for a specific company's SmartRecruiters ATS."""

    platform = "smartrecruiters"

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
        return [
            {**job, "company": self.display_name}
            for job in raw_jobs
        ]

    @classmethod
    def from_registry(cls, entry: dict[str, Any]) -> "SmartRecruitersCrawler":
        return cls(
            company_id=entry["id"],
            display_name=entry["company"],
            board_token=entry["board_token"],
            locations=entry.get("locations", []),
        )
