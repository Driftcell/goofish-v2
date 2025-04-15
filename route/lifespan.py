import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from db import MongoDB

from .sche import init_scheduler
from .task import start_im_task_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用程序生命周期管理器
    
    管理FastAPI应用程序的启动和关闭过程，包括初始化数据库连接、
    启动调度器以及启动IM任务调度器等。应用关闭时负责清理资源。
    
    Args:
        app (FastAPI): FastAPI应用程序实例
        
    Yields:
        None: 控制权交给应用程序运行
        
    Notes:
        - 在应用程序启动时初始化MongoDB连接
        - 启动任务调度器
        - 启动IM任务调度器
        - 应用程序关闭时取消并清理IM调度器任务
    """
    MONGO_URI = os.getenv("MONGO_URI")
    MONGO_DB = os.getenv("MONGO_DB")
    assert MONGO_URI is not None and MONGO_DB is not None

    MongoDB(MONGO_URI, MONGO_DB)
    init_scheduler()
    
    # Start the IM task scheduler
    im_scheduler_task = asyncio.create_task(start_im_task_scheduler())
    
    yield
    
    # Cancel the scheduler task when shutting down
    if im_scheduler_task and not im_scheduler_task.done():
        im_scheduler_task.cancel()
        try:
            await im_scheduler_task
        except asyncio.CancelledError:
            pass
