import logging
import time

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.sync_tracker import buy_sync_tracker, sell_sync_tracker
from app.db.base import AsyncSessionLocal
from app.models.enums import Intent
from app.services.scanner_service import (
    sync_and_scan_orders,
)

scheduler = AsyncIOScheduler()


logger = logging.getLogger(__name__)


def init_scheduler(bp, scanner) -> AsyncIOScheduler:
    scheduler.add_job(
        _run_buyorder_sync,
        trigger="interval",
        minutes=60,
        id="run_buyorder_sync",
        kwargs={"bp": bp, "scanner": scanner},
    )
    scheduler.add_job(
        _run_sellorder_sync,
        trigger="interval",
        hours=2,
        id="run_sellorder_sync",
        kwargs={"bp": bp, "scanner": scanner},
    )
    return scheduler


async def _run_buyorder_sync(bp, scanner):
    logger.info("Starting scheduled sync and scan")
    start_time = time.time()
    buy_sync_tracker.start()
    try:
        async with AsyncSessionLocal() as db:
            await sync_and_scan_orders(db, bp, scanner, buy_sync_tracker, Intent.buy)
    except Exception as e:
        logger.exception("Scheduled buyorder sync failed: %s", e)
        buy_sync_tracker.fail(str(e))
    else:
        elapsed_time = time.time() - start_time
        buy_sync_tracker.complete(elapsed_time)
        logger.info("Job completed in %.2fs", elapsed_time)


async def _run_sellorder_sync(bp, scanner):
    logger.info("Starting scheduled sellorder sync")
    start_time = time.time()
    sell_sync_tracker.start()
    try:
        async with AsyncSessionLocal() as db:
            await sync_and_scan_orders(db, bp, scanner, sell_sync_tracker, Intent.sell)
    except Exception as e:
        logger.exception("Scheduled sellorder sync failed: %s", e)
        sell_sync_tracker.fail(str(e))
    else:
        elapsed_time = time.time() - start_time
        sell_sync_tracker.complete(elapsed_time)
        logger.info("Job completed in %.2fs", elapsed_time)
