import logging
from app.services.scanner_service import refresh_buyorder_states
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.listing_service import sync_listings
from app.db.base import AsyncSessionLocal
import time
from datetime import datetime

scheduler = AsyncIOScheduler()


logger = logging.getLogger(__name__)


def init_scheduler(bp, scanner) -> AsyncIOScheduler:
    scheduler.add_job(
        _sync_and_scan,
        trigger="interval",
        minutes=15,
        # next_run_time=datetime.now(),
        id="sync_and_scan",
        kwargs={"bp": bp, "scanner": scanner},
    )
    return scheduler


async def _sync_and_scan(bp, scanner):
    logger.info("Starting scheduled sync and scan")
    start_time = time.time()
    try:
        async with AsyncSessionLocal() as db:
            listings = await sync_listings(db, bp, sync_all=True)
            logger.info("Synced %d listings", len(listings))

            await refresh_buyorder_states(db, scanner)
    except Exception as e:
        logger.exception("Scheduled sync and scan failed: %s", e)
    elapsed_time = time.time() - start_time
    logger.info("Job completed in %.2fs", elapsed_time)
