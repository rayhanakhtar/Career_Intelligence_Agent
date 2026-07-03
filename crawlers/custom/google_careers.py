"""Crawler for Google Careers."""

import json
import logging
from typing import Any

from bs4 import BeautifulSoup

from crawlers.base import BaseCrawler
from crawlers.utils import get_with_retry

logger = logging.getLogger(__name__)

GOOGLE_CAREERS_URL = "https://careers.google.com/jobs/results/"


def _parse_jobs_from_html(html: str) -> list[dict[str, str]]:
    """Parse Google Careers HTML for job listings embedded in script tags."""
    jobs: list[dict[str, str]] = []
    soup = BeautifulSoup(html, "html.parser")

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(data, list):
            data = [data]
        for item in data:
            if not isinstance(item, dict):
                continue
            if item.get("@type") == "JobPosting":
                jobs.append({
                    "title": item.get("title", ""),
                    "location": item.get("jobLocation", {}).get("address", {}).get("addressLocality", ""),
                    "description": item.get("description", ""),
                    "apply_url": item.get("url", ""),
                    "posted_at": item.get("datePosted", ""),
                    "department": "",
                    "employment_type": item.get("employmentType", ""),
                })
    return jobs


class GoogleCrawler(BaseCrawler):
    """Crawler for Google Careers."""

    platform = "google_careers"

    def __init__(
        self,
        company_id: str,
        display_name: str,
        locations: list[str] | None = None,
    ) -> None:
        super().__init__(company_id, display_name, locations)

    def fetch_jobs(self) -> list[dict[str, Any]]:
        response = get_with_retry(GOOGLE_CAREERS_URL)
        if response is None:
            logger.error("Failed to fetch Google Careers page")
            return []

        raw_jobs = _parse_jobs_from_html(response.text)
        logger.info("Parsed %d jobs from Google Careers", len(raw_jobs))
        return [
            {
                "title": j["title"],
                "company": self.display_name,
                "location": j["location"],
                "description": j["description"],
                "apply_url": j["apply_url"],
                "department": j["department"],
                "employment_type": j["employment_type"],
                "posted_at": j["posted_at"],
                "source": "google_careers",
                "source_id": j["apply_url"],
            }
            for j in raw_jobs
        ]

    @classmethod
    def from_registry(cls, entry: dict[str, Any]) -> "GoogleCrawler":
        return cls(
            company_id=entry["id"],
            display_name=entry["company"],
            locations=entry.get("locations", []),
        )
