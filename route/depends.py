import os

from fastapi import HTTPException, Request
from minio import Minio
from motor.motor_asyncio import AsyncIOMotorDatabase

from db import MongoDB


def get_token(request: Request) -> str:
    token = getattr(request.state, "token", None)
    if token is None:
        raise HTTPException(status_code=401, detail="X-TOKEN header missing")
    return token


async def get_db() -> AsyncIOMotorDatabase:
    return MongoDB.get_db()


async def get_minio() -> Minio:
    minio_client = Minio(
        endpoint=os.getenv("MINIO_ENDPOINT"),  # type: ignore
        access_key=os.getenv("MINIO_ACCESS_KEY"),
        secret_key=os.getenv("MINIO_SECRET_KEY"),
        secure=False,
    )

    return minio_client
