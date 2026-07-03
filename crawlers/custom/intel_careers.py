"""Crawler for Intel Careers."""

import logging
from typing import Any

from bs4 import BeautifulSoup

from crawlers.base import BaseCrawler
from crawlers.utils import get_with_retry

logger = logging.getLogger(__name__)

INTEL_CAREERS_URL = "https://jobs.intel.com/"


def _parse_jobs_from_html(html: str) -> list[dict[str, str]]:
    """Parse Intel Careers HTML for job listings."""
    jobs: list[dict[str, str]] = []
    soup = BeautifulSoup(html, "html.parser")

    for card in soup.select("[class*='job'], [class*='position'], .job-listing, [data-job-id], tr"):
        title_el = card.select_one("a[class*='title'], .job-title a, h3 a, a[href*='/job/']")
        loc_el = card.select_one("[class*='location'], .job-location, [data-location]")
        dept_el = card.select_one("[class*='category'], [class*='dept'], .job-category")
        date_el = card.select_one("[class*='date'], [class*='posted'], time, .posting-date")

        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            continue

        href = title_el.get("href", "") if title_el else ""
        apply_url = href if href.startswith("http") else f"https://jobs.intel.com{href}" if href else ""

        jobs.append({
            "title": title,
            "location": loc_el.get_text(strip=True) if loc_el else "",
            "description": "",
            "apply_url": apply_url,
            "department": dept_el.get_text(strip=True) if dept_el else "",
            "employment_type": "",
            "posted_at": date_el.get_text(strip=True) if date_el else "",
        })

    return jobs


class IntelCrawler(BaseCrawler):
    """Crawler for Intel Careers."""

    platform = "intel_careers"

    def __init__(
        self,
        company_id: str,
        display_name: str,
        locations: list[str] | None = None,
    ) -> None:
        super().__init__(company_id, display_name, locations)

    def fetch_jobs(self) -> list[dict[str, Any]]:
        response = get_with_retry(INTEL_CAREERS_URL)
        if response is None:
            logger.error("Failed to fetch Intel Careers page")
            return []

        raw_jobs = _parse_jobs_from_html(response.text)
        logger.info("Parsed %d jobs from Intel Careers", len(raw_jobs))
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
                "source": "intel_careers",
                "source_id": j["apply_url"],
            }
            for j in raw_jobs
        ]

    @classmethod
    def from_registry(cls, entry: dict[str, Any]) -> "IntelCrawler":
        return cls(
            company_id=entry["id"],
            display_name=entry["company"],
            locations=entry.get("locations", []),
        )
