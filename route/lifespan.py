import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from db import MongoDB

from .sche import init_scheduler
from .task import start_im_task_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
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
