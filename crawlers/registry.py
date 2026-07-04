"""Company registry and crawler class mapping."""

import json
import logging
import os
from pathlib import Path
from typing import Any, cast

import yaml

from crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

_COMPANIES_PATH = os.getenv("COMPANIES_PATH", os.path.join("data", "companies.yml"))

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


def _resolve_registry_path(path: str | None) -> str:
    """Resolve the registry file path, falling back from YAML to JSON.

    Args:
        path: Explicit path, or ``None`` to use the default.

    Returns:
        A file path that exists, or the requested path if nothing exists.
    """
    p = path or _COMPANIES_PATH

    # If an explicit path was given, use it as-is.
    if path is not None:
        return p

    # Default path: prefer .yml, fall back to .json for backward compat.
    p_path = Path(p)
    if not p_path.exists():
        json_fallback = p_path.with_suffix(".json")
        if json_fallback.exists():
            logger.info("YAML registry not found, falling back to %s", json_fallback)
            return str(json_fallback)

    return p


def _load_yaml(path: str) -> list[dict[str, Any]]:
    """Load companies from a YAML file.

    Expects a top-level ``companies`` key containing a list.
    """
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if isinstance(data, dict):
        data = data.get("companies", [])
    if not isinstance(data, list):
        logger.warning("Unexpected YAML structure in %s — expected a list under 'companies'", path)
        return []
    return data


def _load_json(path: str) -> list[dict[str, Any]]:
    """Load companies from a JSON file (top-level list)."""
    with open(path, encoding="utf-8") as f:
        return cast(list[dict[str, Any]], json.load(f))


def load_companies(path: str | None = None) -> list[dict[str, Any]]:
    """Load the company registry from a YAML or JSON file.

    Detects format by file extension (``.yml``/``.yaml`` vs ``.json``).
    Defaults to ``data/companies.yml`` with a fallback to ``data/companies.json``.

    Args:
        path: Path to the registry file. If ``None``, uses the default path.

    Returns:
        A list of company dicts.
    """
    p = _resolve_registry_path(path)
    try:
        data = _load_yaml(p) if p.endswith((".yml", ".yaml")) else _load_json(p)
        logger.info("Loaded %d companies from %s", len(data), p)
        return data
    except FileNotFoundError:
        logger.warning("Company registry not found at %s — returning empty list", p)
        return []
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        logger.error("Invalid registry file %s: %s", p, e)
        return []


def save_companies(companies: list[dict[str, Any]], path: str | None = None) -> None:
    """Save the company registry to a YAML or JSON file.

    Detects format by file extension (``.yml``/``.yaml`` vs ``.json``).

    Args:
        companies: List of company dicts.
        path: Path to write to. Defaults to ``data/companies.yml``.
    """
    p = path or _COMPANIES_PATH
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if p.endswith((".yml", ".yaml")):
        with open(p, "w", encoding="utf-8") as f:
            yaml.dump({"companies": companies}, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    else:
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
