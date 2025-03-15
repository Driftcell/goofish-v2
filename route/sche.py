import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

scheduler = AsyncIOScheduler()

def init_scheduler():
    """
    Initialize the scheduler and start it.
    """
    scheduler.start()
    logger.info("Scheduler started.")
