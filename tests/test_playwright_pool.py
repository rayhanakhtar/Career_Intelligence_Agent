"""Tests for PlaywrightPool."""

from crawlers.playwright_pool import PlaywrightPool


class TestPlaywrightPool:
    """Tests for PlaywrightPool."""

    def test_init_sets_max_browsers(self):
        """The constructor should store max_browsers."""
        pool = PlaywrightPool(max_browsers=5)
        assert pool._max_browsers == 5
        assert pool._closed is False

    def test_init_default_max_browsers(self):
        """max_browsers should default to 3."""
        pool = PlaywrightPool()
        assert pool._max_browsers == 3

    def test_close_idempotent(self):
        """Calling close() multiple times should not raise."""
        pool = PlaywrightPool()
        import asyncio
        asyncio.run(pool.close())
        asyncio.run(pool.close())  # Second call should be no-op.
        assert pool._closed is True

    def test_fetch_page_returns_none_when_playwright_missing(self):
        """fetch_page should return None when Playwright is not installed."""
        pool = PlaywrightPool()
        import asyncio
        result = asyncio.run(pool.fetch_page("https://example.com"))
        assert result is None

    def test_fetch_page_returns_none_when_closed(self):
        """fetch_page should return None when the pool is closed."""
        pool = PlaywrightPool()
        pool._closed = True
        import asyncio
        result = asyncio.run(pool.fetch_page("https://example.com"))
        assert result is None


class TestPlaywrightPoolSingleton:
    """Tests for the module-level get_pool / close_pool functions."""

    def test_get_pool_returns_singleton(self):
        """get_pool should return the same instance on repeated calls."""
        from crawlers.playwright_pool import get_pool, close_pool
        import asyncio

        asyncio.run(close_pool())  # Reset.

        p1 = get_pool()
        p2 = get_pool()
        assert p1 is p2

        asyncio.run(close_pool())

    def test_close_pool_resets_singleton(self):
        """close_pool should reset the singleton to None."""
        from crawlers.playwright_pool import get_pool, close_pool, _pool
        import asyncio

        asyncio.run(close_pool())  # Reset.
        p1 = get_pool()
        asyncio.run(close_pool())
        assert _pool is None
        p2 = get_pool()
        assert p2 is not p1

        asyncio.run(close_pool())
