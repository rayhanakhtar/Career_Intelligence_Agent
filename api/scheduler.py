"""APScheduler integration for periodic crawl execution."""

import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from crawlers.service import CrawlService

logger = logging.getLogger(__name__)


class CrawlScheduler:
    """Manages a periodic crawl-all job via APScheduler.

    Reads ``SCHEDULER_ENABLED`` and ``SCHEDULER_INTERVAL_HOURS`` from the
    environment. Attach to a FastAPI app via the ``lifespan`` context manager::

        @asynccontextmanager
        async def lifespan(app):
            scheduler = CrawlScheduler()
            scheduler.start()
            yield
            scheduler.stop()

    Usage:
        app = FastAPI(lifespan=lifespan)
    """

    def __init__(self, db_path: str | None = None) -> None:
        self.scheduler = AsyncIOScheduler()
        self.db_path = db_path if db_path is not None else os.getenv("DATABASE_PATH", "jobs.db")
        self.enabled = os.getenv("SCHEDULER_ENABLED", "true").lower() in ("true", "1", "yes")
        self.interval_hours = int(os.getenv("SCHEDULER_INTERVAL_HOURS", "6"))

    def start(self) -> None:
        """Register the crawl-all job and start the scheduler (if enabled)."""
        if not self.enabled:
            logger.info("Periodic crawl is disabled (SCHEDULER_ENABLED=false)")
            return

        self.scheduler.add_job(
            self._run_crawl_all,
            trigger="interval",
            hours=self.interval_hours,
            id="crawl_all",
            replace_existing=True,
            max_instances=1,
        )
        self.scheduler.start()
        logger.info(
            "Periodic crawl enabled — will crawl all companies every %d hour(s)",
            self.interval_hours,
        )

    async def _run_crawl_all(self) -> None:
        """Execute a full crawl of all enabled companies."""
        logger.info("[Scheduler] Starting scheduled crawl-all")
        service = CrawlService(self.db_path)
        service.crawl_all()
        logger.info("[Scheduler] Scheduled crawl-all finished")

    def stop(self) -> None:
        """Shut down the scheduler gracefully."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler shut down")
