"""Crawler for Workday ATS via the public Jobs API."""

import json
import logging
import time
from typing import Any

import requests

from crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

WORKDAY_API_BASE = "https://{subdomain}.myworkdayjobs.com/wday/cxs/{subdomain}/{tenant}/jobs"
_PAGE_SIZE = 20
_MAX_PAGE_RETRIES = 3


def _fetch_page(
    subdomain: str,
    tenant: str,
    offset: int = 0,
    limit: int = _PAGE_SIZE,
) -> dict[str, Any] | None:
    """Fetch a single page of jobs from the Workday Jobs API with retry.

    Args:
        subdomain: Workday subdomain (e.g. ``"wd1"``, ``"wd5"``).
        tenant: Tenant name (e.g. ``"Adobe"``).
        offset: Pagination offset (0-based).
        limit: Page size.

    Returns:
        Parsed JSON response dict, or ``None`` after exhausting retries.
    """
    url = WORKDAY_API_BASE.format(subdomain=subdomain, tenant=tenant)
    payload = {"limit": limit, "offset": offset, "searchText": ""}
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    last_error: Exception | None = None
    for attempt in range(1, _MAX_PAGE_RETRIES + 1):
        try:
            if attempt > 1:
                backoff = 2 ** (attempt - 1)
                logger.info(
                    "Retry %d/%d for Workday %s/%s offset=%d (backoff=%ds)",
                    attempt - 1, _MAX_PAGE_RETRIES, subdomain, tenant, offset, backoff,
                )
                time.sleep(backoff)

            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout as e:
            last_error = e
            logger.warning("Timeout on Workday %s/%s offset=%d (attempt %d/%d)", subdomain, tenant, offset, attempt, _MAX_PAGE_RETRIES)
        except requests.exceptions.HTTPError as e:
            last_error = e
            status = e.response.status_code if e.response is not None else 0
            logger.warning("HTTP %d on Workday %s/%s offset=%d (attempt %d/%d)", status, subdomain, tenant, offset, attempt, _MAX_PAGE_RETRIES)
            if status in (401, 403):
                break
        except requests.exceptions.ConnectionError as e:
            last_error = e
            logger.warning("Connection error on Workday %s/%s offset=%d (attempt %d/%d)", subdomain, tenant, offset, attempt, _MAX_PAGE_RETRIES)
        except requests.exceptions.RequestException as e:
            last_error = e
            logger.warning("Request failed for Workday %s/%s offset=%d (attempt %d/%d): %s", subdomain, tenant, offset, attempt, _MAX_PAGE_RETRIES, e)

    logger.error("All retries exhausted for Workday %s/%s offset=%d: %s", subdomain, tenant, offset, last_error)
    return None


def _extract_workplace_type(raw: dict[str, Any]) -> str:
    """Extract workplace/remote type from a Workday job posting."""
    remote_type = raw.get("remoteType")
    if isinstance(remote_type, dict):
        remote_type = remote_type.get("label") or remote_type.get("value") or ""
    if remote_type:
        if "remote" in str(remote_type).lower():
            return "Remote"
        elif "hybrid" in str(remote_type).lower():
            return "Hybrid"
        else:
            return "On-site"
    return ""


def _build_job_record(raw: dict[str, Any], display_name: str, tenant: str, subdomain: str) -> dict[str, Any]:
    """Normalise a raw Workday job dict into the standard job record format."""
    ext_path = raw.get("externalPath") or ""
    if ext_path.startswith("/"):
        apply_url = f"https://{subdomain}.myworkdayjobs.com{ext_path}"
    else:
        apply_url = ""

    categories = raw.get("categories")
    department = ""
    if isinstance(categories, list) and categories:
        first_cat = categories[0]
        if isinstance(first_cat, dict):
            department = first_cat.get("name") or ""

    description_raw = raw.get("description")
    description = ""
    if isinstance(description_raw, dict):
        description = description_raw.get("text") or ""
    elif isinstance(description_raw, str):
        description = description_raw

    workplace_type = _extract_workplace_type(raw)
    location = raw.get("locationsText") or ""
    if workplace_type and workplace_type not in location:
        location = f"{location} ({workplace_type})" if location else workplace_type

    return {
        "title": raw.get("title") or "",
        "company": display_name,
        "location": location,
        "description": description,
        "apply_url": apply_url,
        "department": department,
        "employment_type": raw.get("type") or raw.get("employmentType") or "",
        "posted_at": raw.get("postedOnDate") or "",
        "source": "workday",
        "source_id": str(raw.get("jobPostingId") or raw.get("id") or ""),
    }


def fetch_jobs(subdomain: str, tenant: str) -> list[dict[str, Any]]:
    """Fetch all active jobs from a Workday tenant.

    Args:
        subdomain: Workday subdomain (e.g. ``"wd1"``, ``"wd5"``).
        tenant: Tenant name (e.g. ``"Microsoft"``, ``"Adobe"``).

    Returns:
        A list of standardised job record dictionaries.
    """
    all_jobs: list[dict[str, Any]] = []
    offset = 0
    page_count = 0
    t0 = time.time()

    while True:
        data = _fetch_page(subdomain, tenant, offset=offset)
        if data is None:
            break

        job_postings = data.get("jobPostings")
        if not isinstance(job_postings, list):
            logger.warning("No jobPostings array in Workday response for %s/%s at offset %d", subdomain, tenant, offset)
            break

        all_jobs.extend(job_postings)
        page_count += 1

        total = data.get("total", 0)
        if not isinstance(total, (int, float)) or offset + len(job_postings) >= total:
            break

        offset += len(job_postings)

    elapsed = time.time() - t0
    logger.info(
        "Fetched %d jobs from Workday tenant %s/%s (%d pages, %.2fs)",
        len(all_jobs), subdomain, tenant, page_count, elapsed,
    )

    return [
        _build_job_record(job, tenant, tenant, subdomain)
        for job in all_jobs
    ]


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
        raw_jobs = fetch_jobs(self.subdomain, self.tenant)
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
