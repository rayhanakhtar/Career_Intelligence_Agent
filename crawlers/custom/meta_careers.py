"""Crawler for Meta Careers."""

import json
import logging
from typing import Any

from bs4 import BeautifulSoup

from crawlers.base import BaseCrawler
from crawlers.utils import get_with_retry

logger = logging.getLogger(__name__)

META_CAREERS_URL = "https://www.metacareers.com/jobs/"


def _parse_jobs_from_html(html: str) -> list[dict[str, str]]:
    """Parse Meta Careers HTML for embedded job data."""
    jobs: list[dict[str, str]] = []
    soup = BeautifulSoup(html, "html.parser")

    for script in soup.find_all("script"):
        if not script.string:
            continue
        text = script.string.strip()
        if text.startswith("window.__INITIAL_STATE__"):
            try:
                json_str = text.split("=", 1)[1].strip().rstrip(";")
                data = json.loads(json_str)
                job_list = data.get("jobs", {}).get("availableJobs", [])
                for job in job_list:
                    jobs.append(
                        {
                            "title": job.get("title", ""),
                            "location": job.get("location", ""),
                            "description": job.get("description", ""),
                            "apply_url": f"https://www.metacareers.com/jobs/{job.get('id', '')}",
                            "department": "",
                            "employment_type": job.get("employmentType", ""),
                            "posted_at": job.get("postedDate", ""),
                        }
                    )
            except (json.JSONDecodeError, AttributeError):
                continue

    return jobs


class MetaCrawler(BaseCrawler):
    """Crawler for Meta Careers."""

    platform = "meta_careers"

    def __init__(
        self,
        company_id: str,
        display_name: str,
        locations: list[str] | None = None,
    ) -> None:
        super().__init__(company_id, display_name, locations)

    def fetch_jobs(self) -> list[dict[str, Any]]:
        response = get_with_retry(META_CAREERS_URL)
        if response is None:
            logger.error("Failed to fetch Meta Careers page")
            return []

        raw_jobs = _parse_jobs_from_html(response.text)
        logger.info("Parsed %d jobs from Meta Careers", len(raw_jobs))
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
                "source": "meta_careers",
                "source_id": j["apply_url"],
            }
            for j in raw_jobs
        ]

    @classmethod
    def from_registry(cls, entry: dict[str, Any]) -> "MetaCrawler":
        return cls(
            company_id=entry["id"],
            display_name=entry["company"],
            locations=entry.get("locations", []),
        )
