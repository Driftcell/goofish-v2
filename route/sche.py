import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

scheduler = AsyncIOScheduler()

def init_scheduler():
    """
    初始化并启动任务调度器
    
    初始化AsyncIOScheduler实例并启动，用于管理应用中的定时任务。
    
    Returns:
        None: 此函数通过副作用工作，不返回值
    """
    scheduler.start()
    logger.info("Scheduler started.")
