"""Crawler for Amazon Jobs."""

import logging
from typing import Any

from bs4 import BeautifulSoup

from crawlers.base import BaseCrawler
from crawlers.utils import get_with_retry

logger = logging.getLogger(__name__)

AMAZON_JOBS_URL = "https://www.amazon.jobs/en-gb/search?base_query=&offset=0&result_limit=20"


def _parse_jobs_from_html(html: str) -> list[dict[str, str]]:
    """Parse Amazon Jobs HTML for job listings."""
    jobs: list[dict[str, str]] = []
    soup = BeautifulSoup(html, "html.parser")

    for card in soup.select("[data-job-id]"):
        title_el = card.select_one("h3 a, .job-title a, h3")
        loc_el = card.select_one("[data-location], .location, .job-location")
        url_el = card.select_one("a[href*='/jobs/']")
        dept_el = card.select_one(".job-category, .category, .job-department")
        date_el = card.select_one(".posting-date, .date, .job-date")

        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            continue

        location = loc_el.get_text(strip=True) if loc_el else ""
        relative_url = str(url_el.get("href", "")) if url_el else ""
        apply_url = f"https://www.amazon.jobs{relative_url}" if relative_url.startswith("/") else relative_url
        department = dept_el.get_text(strip=True) if dept_el else ""
        posted_at = date_el.get_text(strip=True) if date_el else ""

        jobs.append(
            {
                "title": title,
                "location": location,
                "description": "",
                "apply_url": apply_url,
                "department": department,
                "employment_type": "",
                "posted_at": posted_at,
            }
        )

    return jobs


class AmazonCrawler(BaseCrawler):
    """Crawler for Amazon Jobs."""

    platform = "amazon_careers"

    def __init__(
        self,
        company_id: str,
        display_name: str,
        locations: list[str] | None = None,
    ) -> None:
        super().__init__(company_id, display_name, locations)

    def fetch_jobs(self) -> list[dict[str, Any]]:
        response = get_with_retry(AMAZON_JOBS_URL)
        if response is None:
            logger.error("Failed to fetch Amazon Jobs page")
            return []

        raw_jobs = _parse_jobs_from_html(response.text)
        logger.info("Parsed %d jobs from Amazon Jobs", len(raw_jobs))
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
                "source": "amazon_careers",
                "source_id": j["apply_url"],
            }
            for j in raw_jobs
        ]

    @classmethod
    def from_registry(cls, entry: dict[str, Any]) -> "AmazonCrawler":
        return cls(
            company_id=entry["id"],
            display_name=entry["company"],
            locations=entry.get("locations", []),
        )
