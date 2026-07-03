"""Minimal crawler for TheMathCompany (talent community only — no live jobs)."""

import logging
from typing import Any

from crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)


class MathCompanyCrawler(BaseCrawler):
    """Crawler for TheMathCompany.

    TheMathCompany's career site (mathco.com/careers/) currently uses a
    talent-community signup model with no publicly listed job postings.
    This crawler exists so the company stays in the registry and will
    automatically start returning jobs if they begin posting in the future.
    """

    platform = "mathcompany_careers"

    def fetch_jobs(self) -> list[dict[str, Any]]:
        logger.info("No active job postings for '%s' (talent community only)", self.display_name)
        return []

    @classmethod
    def from_registry(cls, entry: dict[str, Any]) -> "MathCompanyCrawler":
        return cls(
            company_id=entry["id"],
            display_name=entry["company"],
            locations=entry.get("locations", []),
        )
