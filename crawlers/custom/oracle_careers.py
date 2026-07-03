"""Crawler for Oracle Careers."""

import logging
from typing import Any

from bs4 import BeautifulSoup

from crawlers.base import BaseCrawler
from crawlers.utils import get_with_retry

logger = logging.getLogger(__name__)

ORACLE_CAREERS_URL = "https://www.oracle.com/careers/search/"


def _parse_jobs_from_html(html: str) -> list[dict[str, str]]:
    """Parse Oracle Careers HTML for job listings."""
    jobs: list[dict[str, str]] = []
    soup = BeautifulSoup(html, "html.parser")

    for card in soup.select("[class*='job'], [class*='position'], article, tr"):
        title_el = card.select_one("a[class*='title'], h3 a, h4 a, a[href*='careers']")
        loc_el = card.select_one("[class*='location'], [class*='loc'], span[class*='loc']")
        dept_el = card.select_one("[class*='team'], [class*='org'], [class*='department']")
        date_el = card.select_one("[class*='date'], [class*='posted'], time")

        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            continue

        href = title_el.get("href", "") if title_el else ""
        apply_url = href if href.startswith("http") else f"https://www.oracle.com{href}" if href else ""

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


class OracleCrawler(BaseCrawler):
    """Crawler for Oracle Careers."""

    platform = "oracle_careers"

    def __init__(
        self,
        company_id: str,
        display_name: str,
        locations: list[str] | None = None,
    ) -> None:
        super().__init__(company_id, display_name, locations)

    def fetch_jobs(self) -> list[dict[str, Any]]:
        response = get_with_retry(ORACLE_CAREERS_URL)
        if response is None:
            logger.error("Failed to fetch Oracle Careers page")
            return []

        raw_jobs = _parse_jobs_from_html(response.text)
        logger.info("Parsed %d jobs from Oracle Careers", len(raw_jobs))
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
                "source": "oracle_careers",
                "source_id": j["apply_url"],
            }
            for j in raw_jobs
        ]

    @classmethod
    def from_registry(cls, entry: dict[str, Any]) -> "OracleCrawler":
        return cls(
            company_id=entry["id"],
            display_name=entry["company"],
            locations=entry.get("locations", []),
        )
