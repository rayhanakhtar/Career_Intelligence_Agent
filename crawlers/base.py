"""Abstract base class for all job board crawlers."""

from abc import ABC, abstractmethod
from typing import Any, ClassVar


class BaseCrawler(ABC):
    """Abstract base class that all platform-specific crawlers must implement.

    Each subclass represents a crawler for a specific company's job board
    or ATS platform. Subclasses must implement :meth:`fetch_jobs` and
    are expected to return records in a standardised dictionary format.
    """

    platform: ClassVar[str] = ""

    def __init__(
        self,
        company_id: str,
        display_name: str,
        locations: list[str] | None = None,
    ) -> None:
        self.company_id = company_id
        self.display_name = display_name
        self.locations = locations or []

    @abstractmethod
    def fetch_jobs(self) -> list[dict[str, Any]]:
        """Fetch all active job postings for this company.

        Returns:
            A list of job record dictionaries with these keys:
            ``title``, ``company``, ``location``, ``description``,
            ``apply_url``, ``department``, ``employment_type``,
            ``posted_at``, ``source``, ``source_id``.
        """

    @classmethod
    def from_registry(cls, entry: dict[str, Any]) -> "BaseCrawler":
        """Factory: create a crawler instance from a registry entry.

        Args:
            entry: A company dict from ``companies.json``.

        Returns:
            A new crawler instance.
        """
        raise NotImplementedError(
            f"{cls.__name__} must implement from_registry or be instantiated directly"
        )
