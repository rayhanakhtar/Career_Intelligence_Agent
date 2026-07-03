"""Company registry and crawler class mapping."""

import json
import logging
import os
from typing import Any

from crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

_COMPANIES_PATH = os.getenv("COMPANIES_PATH", os.path.join("data", "companies.json"))

_crawler_classes: dict[str, type[BaseCrawler]] = {}


def register_crawler(platform: str, cls: type[BaseCrawler]) -> None:
    """Register a crawler class for a given platform name.

    Args:
        platform: The platform identifier (e.g. ``"greenhouse"``).
        cls: The crawler class (must subclass :class:`BaseCrawler`).
    """
    _crawler_classes[platform] = cls
    logger.debug("Registered crawler %s for platform '%s'", cls.__name__, platform)


def get_crawler_class(platform: str) -> type[BaseCrawler] | None:
    """Return the registered crawler class for *platform*, or ``None``."""
    return _crawler_classes.get(platform)


def load_companies(path: str | None = None) -> list[dict[str, Any]]:
    """Load the company registry from a JSON file.

    Args:
        path: Path to the JSON file. Defaults to ``data/companies.json``.

    Returns:
        A list of company dicts.
    """
    p = path or _COMPANIES_PATH
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info("Loaded %d companies from %s", len(data), p)
        return data
    except FileNotFoundError:
        logger.warning("Company registry not found at %s — returning empty list", p)
        return []
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in company registry %s: %s", p, e)
        return []


def save_companies(companies: list[dict[str, Any]], path: str | None = None) -> None:
    """Save the company registry to a JSON file.

    Args:
        companies: List of company dicts.
        path: Path to write to. Defaults to ``data/companies.json``.
    """
    p = path or _COMPANIES_PATH
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(companies, f, indent=2, ensure_ascii=False)
    logger.info("Saved %d companies to %s", len(companies), p)


def get_enabled_companies(path: str | None = None) -> list[dict[str, Any]]:
    """Return only companies where ``enabled`` is ``true``."""
    return [c for c in load_companies(path) if c.get("enabled", False)]


def get_company(company_id: str, path: str | None = None) -> dict[str, Any] | None:
    """Look up a single company by its ``id`` field.

    Args:
        company_id: The internal company identifier.
        path: Optional path to the registry JSON file.

    Returns:
        The matching company dict, or ``None``.
    """
    for c in load_companies(path):
        if c.get("id") == company_id:
            return c
    return None


def get_companies_by_platform(platform: str, path: str | None = None) -> list[dict[str, Any]]:
    """Return all companies that use a given ATS platform."""
    return [c for c in load_companies(path) if c.get("platform") == platform]


def build_crawlers(
    path: str | None = None,
) -> list[BaseCrawler]:
    """Instantiate a crawler for every enabled company that has a registered
    crawler class.

    Args:
        path: Optional path to the company registry JSON file.

    Returns:
        A list of :class:`BaseCrawler` instances.
    """
    crawlers: list[BaseCrawler] = []
    for entry in get_enabled_companies(path):
        platform = entry.get("platform", "")
        cls = get_crawler_class(platform)
        if cls is None:
            logger.warning(
                "No crawler registered for platform '%s' (company '%s')",
                platform,
                entry.get("company"),
            )
            continue
        crawler = cls.from_registry(entry)
        crawlers.append(crawler)
    logger.info("Built %d crawlers from registry", len(crawlers))
    return crawlers
