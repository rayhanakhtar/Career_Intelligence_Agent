"""Crawler for NVIDIA Careers."""

import logging
from typing import Any

from bs4 import BeautifulSoup

from crawlers.base import BaseCrawler
from crawlers.utils import get_with_retry

logger = logging.getLogger(__name__)

NVIDIA_CAREERS_URL = "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite"


def _parse_jobs_from_html(html: str) -> list[dict[str, str]]:
    """Parse NVIDIA Careers HTML for job listings."""
    jobs: list[dict[str, str]] = []
    soup = BeautifulSoup(html, "html.parser")

    for card in soup.select("[data-automation-id*='job'], [data-job-id], .css-1q2dra3, article[role='article']"):
        title_el = card.select_one("a[data-automation-id='jobTitle'], h3 a, a")
        loc_el = card.select_one("[data-automation-id='jobLocation'], .job-location, [class*='location']")
        date_el = card.select_one("[data-automation-id='postedOn'], .job-date, [class*='posted']")

        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            continue

        href = str(title_el.get("href", "")) if title_el else ""
        apply_url = href if href.startswith("http") else f"https://nvidia.wd5.myworkdayjobs.com{href}" if href else ""

        jobs.append(
            {
                "title": title,
                "location": loc_el.get_text(strip=True) if loc_el else "",
                "description": "",
                "apply_url": apply_url,
                "department": "",
                "employment_type": "",
                "posted_at": date_el.get_text(strip=True) if date_el else "",
            }
        )

    return jobs


class NvidiaCrawler(BaseCrawler):
    """Crawler for NVIDIA Careers."""

    platform = "nvidia_careers"

    def __init__(
        self,
        company_id: str,
        display_name: str,
        locations: list[str] | None = None,
    ) -> None:
        super().__init__(company_id, display_name, locations)

    def fetch_jobs(self) -> list[dict[str, Any]]:
        response = get_with_retry(NVIDIA_CAREERS_URL)
        if response is None:
            logger.error("Failed to fetch NVIDIA Careers page")
            return []

        raw_jobs = _parse_jobs_from_html(response.text)
        logger.info("Parsed %d jobs from NVIDIA Careers", len(raw_jobs))
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
                "source": "nvidia_careers",
                "source_id": j["apply_url"],
            }
            for j in raw_jobs
        ]

    @classmethod
    def from_registry(cls, entry: dict[str, Any]) -> "NvidiaCrawler":
        return cls(
            company_id=entry["id"],
            display_name=entry["company"],
            locations=entry.get("locations", []),
        )
