import os
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.ingestion.run import run_ingestion

logger = logging.getLogger(__name__)

class IngestionScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.enabled = os.getenv("ENABLE_INGESTION_SCHEDULER", "False").lower() in ("true", "1")

    def start_scheduler(self):
        if not self.enabled:
            logger.info("Ingestion scheduler is disabled by default via ENABLE_INGESTION_SCHEDULER=False")
            return

        logger.info("Starting APScheduler daily ingestion cron job...")
        self.scheduler.add_job(
            run_ingestion,
            trigger="cron",
            hour=2,
            minute=0,
            id="daily_scheme_ingestion",
            replace_existing=True
        )
        self.scheduler.start()

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
