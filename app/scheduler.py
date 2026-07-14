import logging
import time

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.sync_tracker import sync_tracker
from app.db.base import AsyncSessionLocal
from app.services.scanner_service import sync_and_scan

scheduler = AsyncIOScheduler()


logger = logging.getLogger(__name__)


def init_scheduler(bp, scanner) -> AsyncIOScheduler:
    scheduler.add_job(
        _run_scheduled_sync,
        trigger="interval",
        minutes=15,
        id="run_scheduled_sync",
        kwargs={"bp": bp, "scanner": scanner},
    )
    return scheduler


async def _run_scheduled_sync(bp, scanner):
    logger.info("Starting scheduled sync and scan")
    start_time = time.time()
    sync_tracker.start()
    try:
        async with AsyncSessionLocal() as db:
            await sync_and_scan(db, bp, scanner, sync_tracker)
    except Exception as e:
        logger.exception("Scheduled sync and scan failed: %s", e)
        sync_tracker.fail(str(e))
    else:
        elapsed_time = time.time() - start_time
        sync_tracker.complete(elapsed_time)
        logger.info("Job completed in %.2fs", elapsed_time)
