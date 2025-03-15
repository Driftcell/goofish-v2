import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from db import MongoDB

from .log import sse_processor


@asynccontextmanager
async def lifespan(app: FastAPI):
    MONGO_URI = os.getenv("MONGO_URI")
    MONGO_DB = os.getenv("MONGO_DB")
    assert MONGO_URI is not None and MONGO_DB is not None

    MongoDB(MONGO_URI, MONGO_DB)

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            sse_processor,
            structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    yield
