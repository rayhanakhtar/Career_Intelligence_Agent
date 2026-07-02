"""Crawler for Greenhouse ATS via the public Job Board API."""

import json
import logging
from typing import Any

from crawlers.utils import get_with_retry

logger = logging.getLogger(__name__)

GREENHOUSE_API_BASE = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


def _build_job_record(raw: dict[str, Any], board_token: str) -> dict[str, Any]:
    """Normalise a raw Greenhouse job dict into the standard job record format.

    Args:
        raw: A single job object from the Greenhouse API response.
        board_token: The company's Greenhouse board token.

    Returns:
        A standardised job record dictionary.
    """
    metadata = raw.get("metadata", [])
    employment_type = ""
    for m in metadata:
        if m.get("id") == 1:  # Employment type
            employment_type = m.get("value", "")
            break

    return {
        "title": raw.get("title", ""),
        "company": board_token,
        "location": raw.get("location", {}).get("name", ""),
        "description": raw.get("content", ""),
        "apply_url": raw.get("absolute_url", ""),
        "department": raw.get("departments", [{}])[0].get("name", "") if raw.get("departments") else "",
        "employment_type": employment_type,
        "posted_at": raw.get("updated_at", ""),
        "source": "greenhouse",
        "source_id": str(raw.get("id", "")),
    }


def fetch_jobs(board_token: str) -> list[dict[str, Any]]:
    """Fetch all active jobs from a Greenhouse board.

    Args:
        board_token: The company's Greenhouse board token
                     (e.g. "boschglobalsof" for Bosch).

    Returns:
        A list of standardised job record dictionaries.
    """
    url = GREENHOUSE_API_BASE.format(token=board_token)
    response = get_with_retry(url)

    if response is None:
        logger.error("Failed to fetch jobs for board token '%s'", board_token)
        return []

    try:
        data = response.json()
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Invalid JSON from Greenhouse API for '%s': %s", board_token, e)
        return []

    jobs = data.get("jobs", [])
    logger.info("Fetched %d jobs from Greenhouse board '%s'", len(jobs), board_token)

    return [_build_job_record(job, board_token) for job in jobs]


def fetch_and_save(board_token: str, output_path: str) -> int:
    """Fetch jobs from a Greenhouse board and save to a JSON file.

    Args:
        board_token: The company's Greenhouse board token.
        output_path: Path to write the JSON output file.

    Returns:
        Number of jobs saved.
    """
    jobs = fetch_jobs(board_token)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)
    logger.info("Saved %d jobs to %s", len(jobs), output_path)
    return len(jobs)
