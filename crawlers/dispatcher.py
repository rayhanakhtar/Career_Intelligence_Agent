"""Orchestrator that runs all enabled crawlers and stores results.

This module is a thin wrapper around :class:`CrawlService` for backward
compatibility. New code should use ``CrawlService`` directly.
"""

import logging

from crawlers.service import CrawlService

logger = logging.getLogger(__name__)


def crawl_all(db_path: str) -> dict[str, int]:
    """Run every enabled crawler from the registry.

    Delegates to :class:`CrawlService`.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        A dict mapping company display names to the number of jobs stored.
    """
    service = CrawlService(db_path)
    return service.crawl_all()
