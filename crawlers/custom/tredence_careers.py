"""Crawler for Tredence Careers (RippleHire ATS)."""

import json
import logging
import re
from typing import Any

import requests

from crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

RIPPLEHIRE_BASE = "https://tredence.ripplehire.com"
RIPPLEHIRE_CAREERS_URL = f"{RIPPLEHIRE_BASE}/candidate/careers"
RIPPLEHIRE_JOB_SEARCH_URL = f"{RIPPLEHIRE_BASE}/candidate/candidatejobsearch"

HEADERS = {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "x-requested-with": "XMLHttpRequest",
    "origin": RIPPLEHIRE_BASE,
}


def _extract_token(html: str) -> str | None:
    match = re.search(r'id="token"\s+value="([^"]+)"', html)
    return match.group(1) if match else None


def _parse_jobs(api_response: dict) -> list[dict[str, str]]:
    """Parse Tredence (RippleHire) API response into standard job records."""
    jobs: list[dict[str, str]] = []
    for item in api_response.get("jobVoList") or []:
        if not isinstance(item, dict):
            continue
        title = (item.get("jobTitle") or "").strip()
        if not title:
            continue
        location = (item.get("jobLocation") or item.get("locations") or "").strip()
        description = (item.get("jobDesc") or "").strip()
        department = (item.get("bussinessUnit") or "").strip()
        source_id = str(item.get("jobSeq") or item.get("jobId") or "")

        jobs.append(
            {
                "title": title,
                "location": location,
                "description": description,
                "apply_url": f"{RIPPLEHIRE_BASE}/candidate/?token={{token}}&source=CAREERSITE#/job/{source_id}",
                "department": department,
                "employment_type": "",
                "posted_at": "",
            }
        )
    return jobs


class TredenceCrawler(BaseCrawler):
    """Crawler for Tredence Careers via RippleHire API."""

    platform = "tredence_careers"

    def __init__(
        self,
        company_id: str,
        display_name: str,
        locations: list[str] | None = None,
    ) -> None:
        super().__init__(company_id, display_name, locations)

    def fetch_jobs(self) -> list[dict[str, Any]]:
        session = requests.Session()

        try:
            r = session.get(RIPPLEHIRE_CAREERS_URL, timeout=30)
            r.raise_for_status()
        except requests.RequestException as e:
            logger.error("Failed to fetch RippleHire careers page: %s", e)
            return []

        token = _extract_token(r.text)
        if not token:
            logger.error("Could not extract token from RippleHire careers page")
            return []

        referer = f"{RIPPLEHIRE_BASE}/candidate/?token={token}&source=CAREERSITE"
        headers = {**HEADERS, "referer": referer}

        payload_data = {
            "careerSiteUrlParams": json.dumps(
                {
                    "page": 0,
                    "search": "*:*",
                    "token": token,
                    "source": "CAREERSITE",
                    "pagesize": 200,
                }
            ),
            "lang": "en",
        }

        try:
            resp = session.post(
                RIPPLEHIRE_JOB_SEARCH_URL,
                data=payload_data,
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error("RippleHire job search request failed for Tredence: %s", e)
            return []
        except ValueError as e:
            logger.error("Invalid JSON from RippleHire API for Tredence: %s", e)
            return []

        raw_jobs = _parse_jobs(data)
        logger.info("Parsed %d jobs from Tredence RippleHire", len(raw_jobs))

        # Fix apply_url with actual token
        for j in raw_jobs:
            j["apply_url"] = j["apply_url"].replace("{token}", token)

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
                "source": "tredence_careers",
                "source_id": j["apply_url"],
            }
            for j in raw_jobs
        ]

    @classmethod
    def from_registry(cls, entry: dict[str, Any]) -> "TredenceCrawler":
        return cls(
            company_id=entry["id"],
            display_name=entry["company"],
            locations=entry.get("locations", []),
        )
