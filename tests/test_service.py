"""Direct unit tests for CrawlService."""

import tempfile
from unittest.mock import MagicMock, patch

from crawlers.service import CrawlService, CrawlSummary, _format_summary


class TestCrawlOne:
    """Tests for CrawlService.crawl_one()."""

    @patch("crawlers.service.get_company")
    @patch("crawlers.service.get_crawler_class")
    @patch("crawlers.service.CrawlService._crawl_and_store")
    @patch("crawlers.service.CrawlService._invalidate_index")
    def test_crawl_one_success(self, mock_invalidate, mock_store, mock_get_cls, mock_get_company):
        """crawl_one should return job count and invalidate index on success."""
        mock_get_company.return_value = {
            "id": "test-co",
            "company": "Test Co",
            "platform": "test",
            "enabled": True,
        }
        mock_cls = MagicMock()
        mock_get_cls.return_value = mock_cls
        mock_store.return_value = 5

        service = CrawlService(":memory:")
        count = service.crawl_one("test-co")

        assert count == 5
        mock_invalidate.assert_called_once()

    @patch("crawlers.service.get_company")
    def test_crawl_one_company_not_found(self, mock_get_company):
        """crawl_one should return 0 when company is not in registry."""
        mock_get_company.return_value = None
        service = CrawlService(":memory:")
        count = service.crawl_one("unknown")
        assert count == 0

    @patch("crawlers.service.get_company")
    def test_crawl_one_company_disabled(self, mock_get_company):
        """crawl_one should return 0 when company is disabled."""
        mock_get_company.return_value = {
            "id": "test-co",
            "company": "Test Co",
            "platform": "test",
            "enabled": False,
        }
        service = CrawlService(":memory:")
        count = service.crawl_one("test-co")
        assert count == 0

    @patch("crawlers.service.get_company")
    def test_crawl_one_unknown_platform(self, mock_get_company):
        """crawl_one should return 0 when no crawler registered for platform."""
        mock_get_company.return_value = {
            "id": "test-co",
            "company": "Test Co",
            "platform": "nonexistent",
            "enabled": True,
        }
        with patch("crawlers.service.get_crawler_class", return_value=None):
            service = CrawlService(":memory:")
            count = service.crawl_one("test-co")
        assert count == 0

    @patch("crawlers.service.get_company")
    @patch("crawlers.service.get_crawler_class")
    def test_crawl_one_does_not_invalidate_on_zero(self, mock_get_cls, mock_get_company):
        """Index should not be invalidated when no jobs were stored."""
        mock_get_company.return_value = {
            "id": "test-co",
            "company": "Test Co",
            "platform": "test",
            "enabled": True,
        }
        mock_cls = MagicMock()
        mock_get_cls.return_value = mock_cls

        with (
            patch("crawlers.service.CrawlService._crawl_and_store", return_value=0),
            patch("crawlers.service.CrawlService._invalidate_index") as mock_invalidate,
        ):
            service = CrawlService(":memory:")
            service.crawl_one("test-co")
        mock_invalidate.assert_not_called()


class TestCrawlAll:
    """Tests for CrawlService.crawl_all()."""

    @patch("crawlers.service.build_crawlers")
    def test_crawl_all_empty_registry(self, mock_build):
        """crawl_all should return empty dict when no crawlers are built."""
        mock_build.return_value = []
        service = CrawlService(":memory:")
        result = service.crawl_all(log_summary=False)
        assert result == {}

    @patch("crawlers.service.build_crawlers")
    def test_crawl_all_counts_by_company(self, mock_build):
        """crawl_all should return a dict of company → job count."""
        from crawlers.base import BaseCrawler

        class MockA(BaseCrawler):
            platform = "mock_a"

            def fetch_jobs(self):
                return [{"title": "A1", "company": self.display_name, "source": "mock"}]

        class MockB(BaseCrawler):
            platform = "mock_b"

            def fetch_jobs(self):
                return [
                    {"title": "B1", "company": self.display_name, "source": "mock"},
                    {"title": "B2", "company": self.display_name, "source": "mock"},
                ]

        mock_build.return_value = [MockA("co_a", "Company A"), MockB("co_b", "Company B")]

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            service = CrawlService(db_path)
            result = service.crawl_all(log_summary=False)
        finally:
            import os

            os.unlink(db_path)

        assert result == {"Company A": 1, "Company B": 2}

    @patch("crawlers.service.build_crawlers")
    def test_crawl_all_exception_isolation(self, mock_build):
        """A single failing crawler should not stop the rest."""
        from crawlers.base import BaseCrawler

        class BrokenCrawler(BaseCrawler):
            platform = "broken"

            def fetch_jobs(self):
                raise RuntimeError("Network error")

        class GoodCrawler(BaseCrawler):
            platform = "good"

            def fetch_jobs(self):
                return [{"title": "Job", "company": self.display_name, "source": "good"}]

        mock_build.return_value = [BrokenCrawler("broken", "Broken Co"), GoodCrawler("good", "Good Co")]

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            service = CrawlService(db_path)
            result = service.crawl_all(log_summary=False)
        finally:
            import os

            os.unlink(db_path)

        assert result == {"Good Co": 1}

    @patch("crawlers.service.build_crawlers")
    def test_crawl_all_no_jobs_not_in_result(self, mock_build):
        """Companies with zero jobs should not appear in the result dict."""
        from crawlers.base import BaseCrawler

        class NoJobsCrawler(BaseCrawler):
            platform = "empty"

            def fetch_jobs(self):
                return []

        class HasJobsCrawler(BaseCrawler):
            platform = "hasjobs"

            def fetch_jobs(self):
                return [{"title": "Job", "company": self.display_name, "source": "hasjobs"}]

        mock_build.return_value = [NoJobsCrawler("empty", "Empty Co"), HasJobsCrawler("has", "Has Co")]

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            service = CrawlService(db_path)
            result = service.crawl_all(log_summary=False)
        finally:
            import os

            os.unlink(db_path)

        assert "Empty Co" not in result
        assert result == {"Has Co": 1}


class TestCrawlMany:
    """Tests for CrawlService.crawl_many()."""

    @patch("crawlers.service.CrawlService.crawl_one")
    @patch("crawlers.service.get_company")
    def test_crawl_many_returns_company_names(self, mock_get_company, mock_crawl_one):
        """crawl_many should return dict of display names to job counts."""
        mock_crawl_one.side_effect = [5, 0, 3]
        mock_get_company.side_effect = [
            {"company": "Company A"},
            {"company": "Company C"},
        ]

        service = CrawlService(":memory:")
        result = service.crawl_many(["co_a", "co_b", "co_c"])

        assert result == {"Company A": 5, "Company C": 3}
        assert mock_crawl_one.call_count == 3


class TestCrawlAndReport:
    """Tests for CrawlService._crawl_and_report()."""

    def test_crawl_and_report_success(self):
        """A successful crawl should return CrawlResult with status success."""
        from crawlers.base import BaseCrawler

        class MockCrawler(BaseCrawler):
            platform = "mock"

            def fetch_jobs(self):
                return [{"title": "Job", "company": self.display_name, "source": "mock"}]

        crawler = MockCrawler("test", "Test Co")
        service = CrawlService(":memory:")
        result = service._crawl_and_report(crawler)

        assert result.status == "success"
        assert result.job_count == 1
        assert result.company == "Test Co"
        assert result.platform == "mock"

    def test_crawl_and_report_no_jobs(self):
        """A crawl returning empty list should return no_jobs status."""
        from crawlers.base import BaseCrawler

        class EmptyCrawler(BaseCrawler):
            platform = "empty"

            def fetch_jobs(self):
                return []

        crawler = EmptyCrawler("test", "Empty Co")
        service = CrawlService(":memory:")
        result = service._crawl_and_report(crawler)

        assert result.status == "no_jobs"
        assert result.job_count == 0

    def test_crawl_and_report_exception(self):
        """A crawler that raises should return failed status."""
        from crawlers.base import BaseCrawler

        class BrokenCrawler(BaseCrawler):
            platform = "broken"

            def fetch_jobs(self):
                raise RuntimeError("Network error")

        crawler = BrokenCrawler("test", "Broken Co")
        service = CrawlService(":memory:")
        result = service._crawl_and_report(crawler)

        assert result.status == "failed"
        assert result.job_count == 0
        assert "Network error" in result.error_message


class TestCrawlAndStore:
    """Tests for CrawlService._crawl_and_store()."""

    def test_crawl_and_store_returns_count(self):
        """_crawl_and_store should return the number of stored jobs."""
        from crawlers.base import BaseCrawler

        class MockCrawler(BaseCrawler):
            platform = "mock"

            def fetch_jobs(self):
                return [{"title": "Job", "company": self.display_name, "source": "mock"}]

        crawler = MockCrawler("test", "Test Co")

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            service = CrawlService(db_path)
            count = service._crawl_and_store(crawler)
        finally:
            import os

            os.unlink(db_path)

        assert count == 1

    def test_crawl_and_store_zero_on_no_jobs(self):
        """_crawl_and_store should return 0 when crawler returns no jobs."""
        from crawlers.base import BaseCrawler

        class EmptyCrawler(BaseCrawler):
            platform = "empty"

            def fetch_jobs(self):
                return []

        crawler = EmptyCrawler("test", "Empty Co")
        service = CrawlService(":memory:")
        count = service._crawl_and_store(crawler)
        assert count == 0

    def test_crawl_and_store_zero_on_exception(self):
        """_crawl_and_store should return 0 when crawler raises."""
        from crawlers.base import BaseCrawler

        class BrokenCrawler(BaseCrawler):
            platform = "broken"

            def fetch_jobs(self):
                raise RuntimeError("fail")

        crawler = BrokenCrawler("test", "Broken Co")
        service = CrawlService(":memory:")
        count = service._crawl_and_store(crawler)
        assert count == 0


class TestFormatSummary:
    """Tests for _format_summary()."""

    def test_format_summary_basic(self):
        """_format_summary should produce a human-readable block."""
        summary = CrawlSummary(
            total_companies=2,
            successful=1,
            no_jobs=1,
            blocked=0,
            failed=0,
            jobs_by_platform={"greenhouse": 5},
            total_jobs=5,
            duration_seconds=125.0,
        )
        text = _format_summary(summary)
        assert "Companies processed: 2" in text
        assert "Successful:      1" in text
        assert "Total jobs:       5" in text
        assert "Duration:         2m 5s" in text
