"""Crawler for Workable ATS via the public Widget API."""

import json
import logging
import time
from typing import Any

from crawlers.base import BaseCrawler
from crawlers.utils import get_with_retry

logger = logging.getLogger(__name__)

WORKABLE_API_BASE = "https://apply.workable.com/api/v1/widget/accounts/{slug}"


def _build_job_record(raw: dict[str, Any], company_name: str) -> dict[str, Any]:
    """Normalise a raw Workable job dict into the standard job record format."""
    employment_type_map = {
        "full-time": "Full-time",
        "part-time": "Part-time",
        "contract": "Contract",
        "temporary": "Temporary",
        "internship": "Intern",
        "freelance": "Freelance",
    }
    raw_emp_type = (raw.get("employment_type") or "").lower()
    employment_type = employment_type_map.get(raw_emp_type, raw_emp_type)

    location = raw.get("location") or {}
    if isinstance(location, dict):
        location_str = location.get("city") or location.get("name") or location.get("country") or ""
    elif isinstance(location, str):
        location_str = location
    else:
        location_str = ""

    return {
        "title": raw.get("title") or "",
        "company": company_name,
        "location": location_str,
        "description": raw.get("description") or raw.get("short_description") or "",
        "apply_url": raw.get("url") or raw.get("apply_url") or "",
        "department": (raw.get("department") or "").replace("department:", "") if raw.get("department") else "",
        "employment_type": employment_type,
        "posted_at": raw.get("published_date") or raw.get("published_on") or raw.get("created_at") or "",
        "source": "workable",
        "source_id": raw.get("id") or raw.get("shortcode") or str(raw.get("url", "")),
    }


def fetch_jobs(slug: str) -> list[dict[str, Any]]:
    """Fetch all active jobs from a Workable company page.

    Args:
        slug: The Workable company slug (e.g. "tiger-analytics"
            from apply.workable.com/tiger-analytics).

    Returns:
        A list of standardised job record dictionaries.
    """
    url = f"{WORKABLE_API_BASE.format(slug=slug)}?details=true"
    t0 = time.time()
    response = get_with_retry(url)
    elapsed = time.time() - t0

    if response is None:
        logger.error("Failed to fetch jobs for Workable slug '%s' (%.2fs)", slug, elapsed)
        return []

    try:
        data = response.json()
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Invalid JSON from Workable API for '%s': %s (%.2fs)", slug, e, elapsed)
        return []

    if isinstance(data, dict):
        raw_jobs = data.get("jobs", [])
    elif isinstance(data, list):
        raw_jobs = data
    else:
        logger.warning("Unexpected response format from Workable API for '%s' (%.2fs)", slug, elapsed)
        return []

    if not isinstance(raw_jobs, list):
        logger.warning("Unexpected jobs format from Workable API for '%s' (%.2fs)", slug, elapsed)
        return []

    logger.info("Fetched %d jobs from Workable slug '%s' (%.2fs)", len(raw_jobs), slug, elapsed)
    return [_build_job_record(job, slug) for job in raw_jobs]


class WorkableCrawler(BaseCrawler):
    """Crawler for a specific company's Workable ATS board."""

    platform = "workable"

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
    def from_registry(cls, entry: dict[str, Any]) -> "WorkableCrawler":
        return cls(
            company_id=entry["id"],
            display_name=entry["company"],
            board_token=entry["board_token"],
            locations=entry.get("locations", []),
        )
