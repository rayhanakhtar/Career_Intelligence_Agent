"""Crawler for Lever ATS via the public Postings API."""

import json
import logging
from typing import Any

from crawlers.base import BaseCrawler
from crawlers.utils import get_with_retry

logger = logging.getLogger(__name__)

LEVER_API_BASE = "https://api.lever.co/v0/postings/{company}?mode=json"


def _build_job_record(raw: dict[str, Any], company_name: str) -> dict[str, Any]:
    """Normalise a raw Lever job dict into the standard job record format.

    Args:
        raw: A single job object from the Lever API response.
        company_name: Value for the ``company`` field (slug or display name).

    Returns:
        A standardised job record dictionary.
    """
    return {
        "title": raw.get("text", ""),
        "company": company_name,
        "location": raw.get("categories", {}).get("location", ""),
        "description": raw.get("description", ""),
        "apply_url": raw.get("hostedUrl", ""),
        "department": raw.get("categories", {}).get("department", ""),
        "employment_type": raw.get("categories", {}).get("commitment", ""),
        "posted_at": raw.get("createdAt", ""),
        "source": "lever",
        "source_id": raw.get("id", ""),
    }


def _fetch_raw_jobs(company: str) -> list[dict[str, Any]]:
    """Low-level: fetch raw job dicts from the Lever API.

    Args:
        company: The Lever company slug.

    Returns:
        A list of raw job dicts from the API, or empty list on failure.
    """
    url = LEVER_API_BASE.format(company=company)
    response = get_with_retry(url)

    if response is None:
        logger.error("Failed to fetch jobs for Lever company '%s'", company)
        return []

    try:
        data = response.json()
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Invalid JSON from Lever API for '%s': %s", company, e)
        return []

    if not isinstance(data, list):
        logger.warning("Unexpected response format from Lever API for '%s'", company)
        return []

    logger.info("Fetched %d jobs from Lever company '%s'", len(data), company)
    return data


def fetch_jobs(company: str) -> list[dict[str, Any]]:
    """Fetch all active job postings from a Lever company page.

    Args:
        company: The company name as it appears in the Lever URL
                 (e.g. "google" for jobs.lever.co/google).

    Returns:
        A list of standardised job record dictionaries.
    """
    raw_jobs = _fetch_raw_jobs(company)
    return [_build_job_record(job, company) for job in raw_jobs]


def fetch_and_save(company: str, output_path: str) -> int:
    """Fetch jobs from a Lever company page and save to a JSON file.

    Args:
        company: The company name as it appears in the Lever URL.
        output_path: Path to write the JSON output file.

    Returns:
        Number of jobs saved.
    """
    jobs = fetch_jobs(company)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)
    logger.info("Saved %d jobs to %s", len(jobs), output_path)
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
