"""Crawler for Lever ATS via the public Postings API."""

import json
import logging
import time
from typing import Any

from crawlers.base import BaseCrawler
from crawlers.utils import get_with_retry

logger = logging.getLogger(__name__)

LEVER_API_BASE = "https://api.lever.co/v0/postings/{company}?mode=json"


def _get_categories(raw: dict[str, Any]) -> dict[str, Any]:
    """Safely extract categories dict from a Lever job."""
    cats = raw.get("categories")
    return cats if isinstance(cats, dict) else {}


def _build_job_record(raw: dict[str, Any], company_name: str) -> dict[str, Any]:
    """Normalise a raw Lever job dict into the standard job record format."""
    categories = _get_categories(raw)

    return {
        "title": raw.get("text") or "",
        "company": company_name,
        "location": categories.get("location") or "",
        "description": raw.get("description") or "",
        "apply_url": raw.get("hostedUrl") or "",
        "department": categories.get("department") or "",
        "employment_type": categories.get("commitment") or "",
        "posted_at": raw.get("createdAt") or raw.get("updatedAt") or "",
        "source": "lever",
        "source_id": raw.get("id") or raw.get("hostedUrl") or "",
    }


def _fetch_raw_jobs(company: str) -> list[dict[str, Any]]:
    """Low-level: fetch raw job dicts from the Lever API."""
    url = LEVER_API_BASE.format(company=company)
    t0 = time.time()
    response = get_with_retry(url)
    elapsed = time.time() - t0

    if response is None:
        logger.error("Failed to fetch jobs for Lever company '%s' (%.2fs)", company, elapsed)
        return []

    try:
        data = response.json()
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Invalid JSON from Lever API for '%s': %s (%.2fs)", company, e, elapsed)
        return []

    if not isinstance(data, list):
        logger.warning("Unexpected response format from Lever API for '%s' (%.2fs)", company, elapsed)
        return []

    logger.info("Fetched %d jobs from Lever company '%s' (%.2fs)", len(data), company, elapsed)
    return data


def fetch_jobs(company: str) -> list[dict[str, Any]]:
    """Fetch all active job postings from a Lever company page."""
    raw_jobs = _fetch_raw_jobs(company)
    return [_build_job_record(job, company) for job in raw_jobs]


def fetch_and_save(company: str, output_path: str) -> int:
    """Fetch jobs from a Lever company page and save to a JSON file."""
    t0 = time.time()
    jobs = fetch_jobs(company)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)
    logger.info("Saved %d jobs to %s (%.2fs)", len(jobs), output_path, time.time() - t0)
    return len(jobs)


class LeverCrawler(BaseCrawler):
    """Crawler for a specific company's Lever ATS board."""

    platform = "lever"

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
        raw_jobs = _fetch_raw_jobs(self.board_token)
        return [_build_job_record(job, self.display_name) for job in raw_jobs]

    @classmethod
    def from_registry(cls, entry: dict[str, Any]) -> "LeverCrawler":
        return cls(
            company_id=entry["id"],
            display_name=entry["company"],
            board_token=entry["board_token"],
            locations=entry.get("locations", []),
        )
