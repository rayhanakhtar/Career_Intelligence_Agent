"""Crawler for Lever ATS via the public Postings API."""

import json
import logging
from typing import Any

from crawlers.utils import get_with_retry

logger = logging.getLogger(__name__)

LEVER_API_BASE = "https://api.lever.co/v0/postings/{company}?mode=json"


def _build_job_record(raw: dict[str, Any], company: str) -> dict[str, Any]:
    """Normalise a raw Lever job dict into the standard job record format.

    Args:
        raw: A single job object from the Lever API response.
        company: The company name used in the Lever API request.

    Returns:
        A standardised job record dictionary.
    """
    return {
        "title": raw.get("text", ""),
        "company": company,
        "location": raw.get("categories", {}).get("location", ""),
        "description": raw.get("description", ""),
        "apply_url": raw.get("hostedUrl", ""),
        "department": raw.get("categories", {}).get("department", ""),
        "employment_type": raw.get("categories", {}).get("commitment", ""),
        "posted_at": raw.get("createdAt", ""),
        "source": "lever",
        "source_id": raw.get("id", ""),
    }


def fetch_jobs(company: str) -> list[dict[str, Any]]:
    """Fetch all active job postings from a Lever company page.

    Args:
        company: The company name as it appears in the Lever URL
                 (e.g. "google" for jobs.lever.co/google).

    Returns:
        A list of standardised job record dictionaries.
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
    return [_build_job_record(job, company) for job in data]


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
