"""Playwright browser pool for JS-rendered career pages.

Provides a caching pool of browser instances (max 3 concurrent) that are
reused across requests to avoid the overhead of launching a browser for
every crawl.
"""

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

_MAX_BROWSERS = 3


class PlaywrightPool:
    """A simple pool that caches Playwright browser instances.

    Usage::

        pool = PlaywrightPool(max_browsers=3)
        html = await pool.fetch_page("https://example.com")
        await pool.close()

    If Playwright is not installed, :meth:`fetch_page` falls back to
    returning ``None`` and logs a warning.
    """

    def __init__(self, max_browsers: int = _MAX_BROWSERS) -> None:
        self._max_browsers = max_browsers
        self._playwright: Any = None
        self._browsers: list[Any] = []
        self._semaphore = asyncio.Semaphore(max_browsers)
        self._closed = False

    async def _ensure_playwright(self) -> None:
        """Lazy-import Playwright and launch browser instances on first use."""
        if self._playwright is not None:
            return
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.warning(
                "Playwright is not installed. Install with: pip install playwright && playwright install chromium"
            )
            self._playwright = False  # Sentinel: not available.
            return

        self._playwright = await async_playwright().start()
        for _ in range(self._max_browsers):
            browser = await self._playwright.chromium.launch(headless=True)
            self._browsers.append(browser)
        logger.info("Launched %d Playwright browser(s)", len(self._browsers))

    async def fetch_page(
        self,
        url: str,
        timeout: int = 30_000,
        wait_until: str = "networkidle",
    ) -> str | None:
        """Fetch a page's rendered HTML using a pooled browser instance.

        Args:
            url: The URL to fetch.
            timeout: Navigation timeout in milliseconds (default 30s).
            wait_until: Playwright ``waitUntil`` strategy
                (default ``"networkidle"``).

        Returns:
            The full page HTML as a string, or ``None`` if Playwright is not
            available or the page fails to load.
        """
        if self._closed:
            logger.warning("PlaywrightPool is closed")
            return None

        await self._ensure_playwright()
        if not self._playwright:
            return None

        async with self._semaphore:
            browser = self._browsers[0]  # Round-robin from pool.
            page = await browser.new_page()
            try:
                await page.goto(url, timeout=timeout, wait_until=wait_until)
                html = await page.content()
                logger.debug("Fetched %s (%d bytes)", url, len(html))
                return html
            except Exception as e:
                logger.warning("Playwright navigation failed for %s: %s", url, e)
                return None
            finally:
                await page.close()

    async def close(self) -> None:
        """Close all browser instances and stop Playwright."""
        if self._closed:
            return
        self._closed = True
        for browser in self._browsers:
            await browser.close()
        if self._playwright and self._playwright is not False:
            await self._playwright.stop()
        self._browsers.clear()
        logger.info("PlaywrightPool closed")


# Module-level singleton for reuse across the application.
_pool: PlaywrightPool | None = None


def get_pool(max_browsers: int = _MAX_BROWSERS) -> PlaywrightPool:
    """Return (or create) the module-level PlaywrightPool singleton.

    Args:
        max_browsers: Maximum concurrent browser instances (default 3).

    Returns:
        The shared :class:`PlaywrightPool` instance.
    """
    global _pool
    if _pool is None:
        _pool = PlaywrightPool(max_browsers=max_browsers)
    return _pool


async def close_pool() -> None:
    """Close the module-level pool singleton."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
