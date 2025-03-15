import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from db import MongoDB

from .log import sse_processor


@asynccontextmanager
async def lifespan(app: FastAPI):
    MONGO_URI = os.getenv("MONGO_URI")
    MONGO_DB = os.getenv("MONGO_DB")
    assert MONGO_URI is not None and MONGO_DB is not None

    MongoDB(MONGO_URI, MONGO_DB)
    yield
