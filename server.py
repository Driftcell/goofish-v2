import sys
import dotenv

dotenv.load_dotenv()


import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from route import AuthRouter, ConfigRouter, ItemRouter, LogRouter, UploadRouter
from route.filter import global_exception_handler
from route.lifespan import lifespan
from route.log import sse_processor
from route.midware import TokenMiddleware
import logging

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        sse_processor,
        structlog.dev.ConsoleRenderer(colors=True),  # Enable colored output
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=logging.INFO,
)

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
app.add_middleware(TokenMiddleware)

app.add_exception_handler(Exception, handler=global_exception_handler)


app.include_router(LogRouter)
app.include_router(ConfigRouter)
app.include_router(AuthRouter)
app.include_router(ItemRouter)
app.include_router(UploadRouter)
