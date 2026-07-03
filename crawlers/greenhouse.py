"""Crawler for Greenhouse ATS via the public Job Board API."""

import json
import logging
import time
from typing import Any

from crawlers.base import BaseCrawler
from crawlers.utils import get_with_retry

logger = logging.getLogger(__name__)

GREENHOUSE_API_BASE = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


def _extract_employment_type(raw: dict[str, Any]) -> str:
    """Extract employment type from Greenhouse job metadata."""
    for m in raw.get("metadata") or []:
        if isinstance(m, dict) and m.get("id") == 1:
            return m.get("value", "")
    return ""


def _extract_department(raw: dict[str, Any]) -> str:
    """Extract department name from job's departments list."""
    departments = raw.get("departments")
    if isinstance(departments, list) and departments:
        first = departments[0]
        if isinstance(first, dict):
            return first.get("name", "")
    return ""


def _build_job_record(raw: dict[str, Any], company_name: str) -> dict[str, Any]:
    """Normalise a raw Greenhouse job dict into the standard job record format."""
    location = raw.get("location")
    location_name = location.get("name", "") if isinstance(location, dict) else ""

    return {
        "title": raw.get("title", "") or "",
        "company": company_name,
        "location": location_name,
        "description": raw.get("content") or "",
        "apply_url": raw.get("absolute_url") or "",
        "department": _extract_department(raw),
        "employment_type": _extract_employment_type(raw),
        "posted_at": raw.get("updated_at") or raw.get("created_at") or "",
        "source": "greenhouse",
        "source_id": str(raw.get("id") or raw.get("absolute_url") or ""),
    }


def _fetch_raw_jobs(board_token: str) -> list[dict[str, Any]]:
    """Low-level: fetch raw job dicts from the Greenhouse API."""
    url = GREENHOUSE_API_BASE.format(token=board_token)
    t0 = time.time()
    response = get_with_retry(url)
    elapsed = time.time() - t0

    if response is None:
        logger.error("Failed to fetch jobs for board token '%s' (%.2fs)", board_token, elapsed)
        return []

    try:
        data = response.json()
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Invalid JSON from Greenhouse API for '%s': %s (%.2fs)", board_token, e, elapsed)
        return []

    jobs = data.get("jobs", [])
    logger.info("Fetched %d jobs from Greenhouse board '%s' (%.2fs)", len(jobs), board_token, elapsed)
    return jobs


def fetch_jobs(board_token: str) -> list[dict[str, Any]]:
    """Fetch all active jobs from a Greenhouse board."""
    raw_jobs = _fetch_raw_jobs(board_token)
    return [_build_job_record(job, board_token) for job in raw_jobs]


def fetch_and_save(board_token: str, output_path: str) -> int:
    """Fetch jobs from a Greenhouse board and save to a JSON file."""
    t0 = time.time()
    jobs = fetch_jobs(board_token)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)
    logger.info("Saved %d jobs to %s (%.2fs)", len(jobs), output_path, time.time() - t0)
    return len(jobs)


class GreenhouseCrawler(BaseCrawler):
    """Crawler for a specific company's Greenhouse ATS board."""

    platform = "greenhouse"

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
    def from_registry(cls, entry: dict[str, Any]) -> "GreenhouseCrawler":
        return cls(
            company_id=entry["id"],
            display_name=entry["company"],
            board_token=entry["board_token"],
            locations=entry.get("locations", []),
        )
