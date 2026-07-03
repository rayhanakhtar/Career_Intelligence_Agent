"""Crawler for Swiggy Careers (MyNextHire ATS)."""

import logging
from typing import Any

import requests

from crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

MYNEXTHIRE_API = "https://swiggy.mynexthire.com/employer/careers/reqlist/get"
MYNEXTHIRE_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "origin": "https://careers.swiggy.com",
    "referer": "https://careers.swiggy.com/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.7827.55 Safari/537.36",
}


def _parse_jobs(api_response: dict) -> list[dict[str, str]]:
    jobs: list[dict[str, str]] = []
    for item in api_response.get("reqDetailsBOList") or []:
        if not isinstance(item, dict):
            continue
        title = (item.get("reqTitle") or "").strip()
        if not title:
            continue
        location = (item.get("location") or item.get("locationAddress") or "").strip()
        exp_min = item.get("expMin")
        exp_max = item.get("expMax")
        exp_str = ""
        if exp_min is not None and exp_max is not None:
            exp_str = f"{int(exp_min)} - {int(exp_max)} Years"
        elif exp_min is not None:
            exp_str = f"{int(exp_min)}+ Years"

        description = (item.get("jdDisplay") or "").strip()
        department = (item.get("buName") or "").strip()
        employment_type = (item.get("employmentType") or "").strip()
        posted_at = (item.get("approvedOn") or "").strip()
        source_id = str(item.get("reqId", ""))

        jobs.append({
            "title": title,
            "location": location,
            "description": description,
            "apply_url": f"https://careers.swiggy.com/#/careers?reqId={source_id}",
            "department": department,
            "employment_type": employment_type,
            "posted_at": posted_at,
        })
    return jobs


class SwiggyCrawler(BaseCrawler):
    """Crawler for Swiggy Careers via MyNextHire API."""

    platform = "swiggy_careers"

    def __init__(
        self,
        company_id: str,
        display_name: str,
        locations: list[str] | None = None,
    ) -> None:
        super().__init__(company_id, display_name, locations)

    def fetch_jobs(self) -> list[dict[str, Any]]:
        try:
            resp = requests.post(
                MYNEXTHIRE_API,
                json={"source": "careers"},
                headers=MYNEXTHIRE_HEADERS,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error("MyNextHire API request failed for Swiggy: %s", e)
            return []
        except ValueError as e:
            logger.error("Invalid JSON from MyNextHire API for Swiggy: %s", e)
            return []

        raw_jobs = _parse_jobs(data)
        logger.info("Parsed %d jobs from Swiggy MyNextHire", len(raw_jobs))
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
                "source": "swiggy_careers",
                "source_id": j["apply_url"],
            }
            for j in raw_jobs
        ]

    @classmethod
    def from_registry(cls, entry: dict[str, Any]) -> "SwiggyCrawler":
        return cls(
            company_id=entry["id"],
            display_name=entry["company"],
            locations=entry.get("locations", []),
        )
