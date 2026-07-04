"""Tests for the dispatcher (crawl_all orchestrator)."""

import sqlite3
import tempfile
from unittest.mock import patch

from crawlers.dispatcher import crawl_all


class TestCrawlAll:
    """Tests for crawl_all()."""

    def test_crawl_all_empty_registry(self):
        """crawl_all should return empty dict when no crawlers are built."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            with patch("crawlers.service.build_crawlers", return_value=[]):
                result = crawl_all(db_path)
            assert result == {}
        finally:
            import os

            os.unlink(db_path)

    @patch("crawlers.service.build_crawlers")
    @patch("crawlers.service.insert_job")
    def test_crawl_all_with_mock_crawlers(self, mock_insert, mock_build):
        """crawl_all should return a summary of per-company job counts."""
        from crawlers.base import BaseCrawler

        class MockCrawlerA(BaseCrawler):
            platform = "mock_a"

            def fetch_jobs(self):
                return [
                    {"title": "Job A1", "company": self.display_name, "source": "mock"},
                    {"title": "Job A2", "company": self.display_name, "source": "mock"},
                ]

        class MockCrawlerB(BaseCrawler):
            platform = "mock_b"

            def fetch_jobs(self):
                return [
                    {"title": "Job B1", "company": self.display_name, "source": "mock"},
                ]

        mock_build.return_value = [
            MockCrawlerA("co_a", "Company A"),
            MockCrawlerB("co_b", "Company B"),
        ]

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            result = crawl_all(db_path)
        finally:
            import os

            os.unlink(db_path)

        assert result == {"Company A": 2, "Company B": 1}
        assert mock_insert.call_count == 3

    @patch("crawlers.service.build_crawlers")
    def test_crawl_all_crawler_exception(self, mock_build):
        """A crawler that raises should be skipped without crashing crawl_all."""
        from crawlers.base import BaseCrawler

        class BrokenCrawler(BaseCrawler):
            platform = "broken"

            def fetch_jobs(self):
                raise RuntimeError("Network error")

        class GoodCrawler(BaseCrawler):
            platform = "good"

            def fetch_jobs(self):
                return [{"title": "Job", "company": self.display_name, "source": "good"}]

        mock_build.return_value = [
            BrokenCrawler("broken", "Broken Co"),
            GoodCrawler("good", "Good Co"),
        ]

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            result = crawl_all(db_path)
        finally:
            import os

            os.unlink(db_path)

        assert result == {"Good Co": 1}

    @patch("crawlers.service.build_crawlers")
    def test_crawl_all_stores_to_db(self, mock_build):
        """Jobs should be persisted in the SQLite database."""
        from crawlers.base import BaseCrawler

        class MockCrawler(BaseCrawler):
            platform = "mock"

            def fetch_jobs(self):
                return [
                    {
                        "title": "Engineer",
                        "company": self.display_name,
                        "location": "Bengaluru",
                        "source": "mock",
                        "source_id": "1",
                    }
                ]

        mock_build.return_value = [
            MockCrawler("test_co", "Test Co"),
        ]

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            result = crawl_all(db_path)
            assert result == {"Test Co": 1}

            conn = sqlite3.connect(db_path)
            try:
                conn.row_factory = sqlite3.Row
                rows = conn.execute("SELECT * FROM jobs").fetchall()
                assert len(rows) == 1
                assert rows[0]["company"] == "Test Co"
                assert rows[0]["title"] == "Engineer"
            finally:
                conn.close()
        finally:
            import os

            os.unlink(db_path)
