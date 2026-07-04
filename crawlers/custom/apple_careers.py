"""Crawler for Apple Careers."""

import json
import logging
import re
from typing import Any

from bs4 import BeautifulSoup

from crawlers.base import BaseCrawler
from crawlers.utils import get_with_retry

logger = logging.getLogger(__name__)

APPLE_CAREERS_URL = "https://jobs.apple.com/en-us/search"


def _parse_jobs_from_html(html: str) -> list[dict[str, str]]:
    """Parse Apple Careers HTML for embedded job data."""
    jobs: list[dict[str, str]] = []
    soup = BeautifulSoup(html, "html.parser")

    for script in soup.find_all("script"):
        if not script.string:
            continue
        text = script.string.strip()
        if "jobPostings" in text or "searchResults" in text:
            try:
                matches = re.findall(r'\{[^{}]*"title"[^{}]*"location"[^{}]*\}', text)
                for match in matches:
                    try:
                        data = json.loads(match)
                        jobs.append(
                            {
                                "title": data.get("title", ""),
                                "location": data.get("location", ""),
                                "description": data.get("description", ""),
                                "apply_url": f"https://jobs.apple.com{data.get('url', '')}" if data.get("url") else "",
                                "department": data.get("team", ""),
                                "employment_type": data.get("employmentType", ""),
                                "posted_at": data.get("postDate", ""),
                            }
                        )
                    except json.JSONDecodeError:
                        continue
            except (ValueError, AttributeError):
                continue

    return jobs


class AppleCrawler(BaseCrawler):
    """Crawler for Apple Careers."""

    platform = "apple_careers"

    def __init__(
        self,
        company_id: str,
        display_name: str,
        locations: list[str] | None = None,
    ) -> None:
        super().__init__(company_id, display_name, locations)

    def fetch_jobs(self) -> list[dict[str, Any]]:
        response = get_with_retry(APPLE_CAREERS_URL)
        if response is None:
            logger.error("Failed to fetch Apple Careers page")
            return []

        raw_jobs = _parse_jobs_from_html(response.text)
        logger.info("Parsed %d jobs from Apple Careers", len(raw_jobs))
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
                "source": "apple_careers",
                "source_id": j["apply_url"],
            }
            for j in raw_jobs
        ]

    @classmethod
    def from_registry(cls, entry: dict[str, Any]) -> "AppleCrawler":
        return cls(
            company_id=entry["id"],
            display_name=entry["company"],
            locations=entry.get("locations", []),
        )
