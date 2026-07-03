"""Crawler for Workday ATS via the public Jobs API."""

import json
import logging
from typing import Any

from crawlers.base import BaseCrawler
from crawlers.utils import get_with_retry

logger = logging.getLogger(__name__)

WORKDAY_API_BASE = "https://{subdomain}.wd1.myworkdayjobs.com/wday/cxs/{subdomain}/{tenant}/jobs"
WORKDAY_CAREERS_BASE = "https://{subdomain}.myworkdayjobs.com/{careers_site}"

_PAGE_SIZE = 20


def _fetch_raw_page(
    subdomain: str,
    tenant: str,
    offset: int = 0,
    limit: int = _PAGE_SIZE,
) -> dict[str, Any] | None:
    """Fetch a single page of jobs from the Workday Jobs API.

    Args:
        subdomain: The Workday instance subdomain (e.g. ``"wd1"``).
        tenant: The tenant name (e.g. ``"Microsoft"``).
        offset: Pagination offset (0-based).
        limit: Page size.

    Returns:
        The parsed JSON response dict, or ``None`` on failure.
    """
    url = WORKDAY_API_BASE.format(subdomain=subdomain, tenant=tenant)
    payload = {"limit": limit, "offset": offset, "searchText": ""}
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    import requests
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error("Workday API request failed for %s/%s: %s", subdomain, tenant, e)
        return None
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Invalid JSON from Workday API for %s/%s: %s", subdomain, tenant, e)
        return None


def _fetch_all_raw_jobs(subdomain: str, tenant: str) -> list[dict[str, Any]]:
    """Fetch all jobs from a Workday tenant with pagination.

    Args:
        subdomain: The Workday instance subdomain.
        tenant: The tenant name.

    Returns:
        A list of raw job posting dicts.
    """
    all_jobs: list[dict[str, Any]] = []
    offset = 0

    while True:
        data = _fetch_raw_page(subdomain, tenant, offset=offset)
        if data is None:
            break

        job_postings = data.get("jobPostings", [])
        all_jobs.extend(job_postings)

        total = data.get("total", 0)
        if offset + len(job_postings) >= total:
            break

        offset += len(job_postings)

    logger.info(
        "Fetched %d jobs from Workday tenant %s/%s",
        len(all_jobs),
        subdomain,
        tenant,
    )
    return all_jobs


def _build_job_record(raw: dict[str, Any], display_name: str, tenant: str, subdomain: str) -> dict[str, Any]:
    """Normalise a raw Workday job dict into the standard job record format.

    Args:
        raw: A single job posting object from the Workday API.
        display_name: The display company name.
        tenant: The Workday tenant name.
        subdomain: The Workday instance subdomain.

    Returns:
        A standardised job record dictionary.
    """
    ext_path = raw.get("externalPath", "")
    careers_site = raw.get("externalPath", "").split("/")[1] if ext_path.startswith("/") else tenant
    apply_url = f"https://{subdomain}.myworkdayjobs.com{ext_path}" if ext_path else ""

    categories = raw.get("categories", [])
    department = categories[0].get("name", "") if categories else ""

    description = raw.get("description", {})
    if isinstance(description, dict):
        description_text = description.get("text", "")
    elif isinstance(description, str):
        description_text = description
    else:
        description_text = ""

    return {
        "title": raw.get("title", ""),
        "company": display_name,
        "location": raw.get("locationsText", ""),
        "description": description_text,
        "apply_url": apply_url,
        "department": department,
        "employment_type": raw.get("type", ""),
        "posted_at": raw.get("postedOnDate", ""),
        "source": "workday",
        "source_id": str(raw.get("jobPostingId", "")),
    }


def fetch_jobs(subdomain: str, tenant: str) -> list[dict[str, Any]]:
    """Fetch all active jobs from a Workday tenant (standalone convenience).

    Args:
        subdomain: The Workday instance subdomain (e.g. ``"wd1"``).
        tenant: The tenant name (e.g. ``"Microsoft"``).

    Returns:
        A list of standardised job record dictionaries.
    """
    raw_jobs = _fetch_all_raw_jobs(subdomain, tenant)
    return [_build_job_record(job, tenant, tenant, subdomain) for job in raw_jobs]


class WorkdayCrawler(BaseCrawler):
    """Crawler for a specific company's Workday ATS."""

    platform = "workday"

    def __init__(
        self,
        company_id: str,
        display_name: str,
        subdomain: str,
        tenant: str,
        locations: list[str] | None = None,
    ) -> None:
        super().__init__(company_id, display_name, locations)
        self.subdomain = subdomain
        self.tenant = tenant

    def fetch_jobs(self) -> list[dict[str, Any]]:
        raw_jobs = _fetch_all_raw_jobs(self.subdomain, self.tenant)
        return [
            _build_job_record(job, self.display_name, self.tenant, self.subdomain)
            for job in raw_jobs
        ]

    @classmethod
    def from_registry(cls, entry: dict[str, Any]) -> "WorkdayCrawler":
        return cls(
            company_id=entry["id"],
            display_name=entry["company"],
            subdomain=entry.get("subdomain", "wd1"),
            tenant=entry.get("tenant", entry["id"]),
            locations=entry.get("locations", []),
        )
