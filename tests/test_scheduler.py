"""Unit tests for the CrawlScheduler."""

from unittest.mock import MagicMock, patch

from api.scheduler import CrawlScheduler


class TestCrawlScheduler:
    """Tests for CrawlScheduler."""

    def test_constructor_defaults(self):
        """Constructor should set sensible defaults from environment."""
        with patch.dict("os.environ", {}, clear=True):
            scheduler = CrawlScheduler()
        assert scheduler.db_path == "jobs.db"
        assert scheduler.enabled is True
        assert scheduler.interval_hours == 6

    def test_constructor_with_env_overrides(self):
        """Environment variables should override constructor defaults."""
        with patch.dict(
            "os.environ",
            {
                "DATABASE_PATH": "/custom/path/db.sqlite",
                "SCHEDULER_ENABLED": "false",
                "SCHEDULER_INTERVAL_HOURS": "12",
            },
            clear=True,
        ):
            scheduler = CrawlScheduler()
        assert scheduler.db_path == "/custom/path/db.sqlite"
        assert scheduler.enabled is False
        assert scheduler.interval_hours == 12

    def test_constructor_with_explicit_db_path(self):
        """Explicit db_path should take precedence over environment."""
        with patch.dict("os.environ", {"DATABASE_PATH": "/env/path/db.sqlite"}, clear=True):
            scheduler = CrawlScheduler(db_path="/explicit/path/db.sqlite")
        assert scheduler.db_path == "/explicit/path/db.sqlite"

    def test_start_when_disabled(self):
        """start() should not add job or start scheduler when disabled."""
        scheduler = CrawlScheduler()
        scheduler.enabled = False

        with (
            patch.object(scheduler.scheduler, "add_job") as mock_add,
            patch.object(scheduler.scheduler, "start") as mock_start,
        ):
            scheduler.start()

        mock_add.assert_not_called()
        mock_start.assert_not_called()

    def test_start_when_enabled(self):
        """start() should add job and start scheduler when enabled."""
        scheduler = CrawlScheduler()
        scheduler.enabled = True

        with (
            patch.object(scheduler.scheduler, "add_job") as mock_add,
            patch.object(scheduler.scheduler, "start") as mock_start,
        ):
            scheduler.start()

        mock_add.assert_called_once()
        args, kwargs = mock_add.call_args
        assert kwargs["trigger"] == "interval"
        assert kwargs["hours"] == 6
        assert kwargs["id"] == "crawl_all"
        assert kwargs["replace_existing"] is True
        assert kwargs["max_instances"] == 1
        mock_start.assert_called_once()

    def test_start_uses_custom_interval(self):
        """start() should use the configured interval hours."""
        with patch.dict("os.environ", {"SCHEDULER_INTERVAL_HOURS": "24"}, clear=True):
            scheduler = CrawlScheduler()
            scheduler.enabled = True

            with (
                patch.object(scheduler.scheduler, "add_job") as mock_add,
                patch.object(scheduler.scheduler, "start"),
            ):
                scheduler.start()

        _, kwargs = mock_add.call_args
        assert kwargs["hours"] == 24

    def test_stop_when_running(self):
        """stop() should shut down a running scheduler."""
        scheduler = CrawlScheduler()
        scheduler.scheduler = MagicMock()
        scheduler.scheduler.running = True

        scheduler.stop()

        scheduler.scheduler.shutdown.assert_called_once_with(wait=False)

    def test_stop_when_not_running(self):
        """stop() should not shut down if scheduler is not running."""
        scheduler = CrawlScheduler()
        scheduler.scheduler = MagicMock()
        scheduler.scheduler.running = False

        scheduler.stop()

        scheduler.scheduler.shutdown.assert_not_called()

    @patch("api.scheduler.CrawlService")
    def test_run_crawl_all_calls_service(self, mock_crawl_service_class):
        """_run_crawl_all should instantiate CrawlService and call crawl_all."""
        mock_instance = MagicMock()
        mock_crawl_service_class.return_value = mock_instance

        scheduler = CrawlScheduler(db_path="test.db")
        import asyncio

        asyncio.run(scheduler._run_crawl_all())

        mock_crawl_service_class.assert_called_once_with("test.db")
        mock_instance.crawl_all.assert_called_once()
