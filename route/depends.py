import os
import json
import hashlib
import structlog

from fastapi import HTTPException, Request
from minio import Minio
from motor.motor_asyncio import AsyncIOMotorDatabase

from db import MongoDB
from .utils import build_config
from .task import tasks, create_task_for_token
from .sche import scheduler

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


async def get_token(request: Request) -> str:
    token = getattr(request.state, "token", None)
    if token is None:
        raise HTTPException(status_code=401, detail="X-TOKEN header missing")

    db = await get_db()

    user = await db.users.find_one({"token": token})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    if user.get("expired", False):
        raise HTTPException(status_code=401, detail="Token expired")

    config = await build_config(token, db)
    keys = ["configt", "filter", "template", "description", "reply", "report"]
    config_keys = config.keys()

    ready = True
    for key in keys:
        if key not in config_keys:
            ready = False
            logger.info(f"Config not ready, missing key", key=key, token=token)
            break

    if not ready:
        logger.info("Task not created because config is not complete", token=token)
        return token

    # Generate a hash of the config to detect changes
    config_hash = hashlib.md5(json.dumps(config, sort_keys=True).encode()).hexdigest()

    if token not in tasks.keys():
        time_delta = int(config["configt"]["time_delta"])
        # Create a task function for this token
        task_function = create_task_for_token(token)
        tasks[token] = task_function

        # Create a scheduled task using the time_delta from config
        task_id = f"task_{token}"

        # If a task with this ID already exists, remove it first
        if scheduler.get_job(task_id):
            scheduler.remove_job(task_id)
            logger.info("Removing existing task before creating new one", token=token, task_id=task_id)

        # Schedule a new task with the current time_delta
        scheduler.add_job(
            task_function,
            "interval",
            seconds=time_delta,
            id=task_id,
            replace_existing=True,
        )

        logger.info(
            "Created new scheduled task", 
            token=token, 
            task_id=task_id, 
            time_delta=time_delta
        )

        # Store the current time_delta and config hash with the task for later comparison
        tasks[token].time_delta = time_delta
        tasks[token].config_hash = config_hash

    else:
        # Check if config changed and update the scheduled task if needed
        config_changed = False
        change_reasons = []

        # Check if time_delta changed
        if "configt" in config and hasattr(tasks[token], "time_delta"):
            new_time_delta = int(config["configt"]["time_delta"])
            if new_time_delta != tasks[token].time_delta:
                config_changed = True
                change_reasons.append(f"time_delta changed from {tasks[token].time_delta} to {new_time_delta}")

        # Check if overall config changed by comparing hashes
        if (
            hasattr(tasks[token], "config_hash")
            and tasks[token].config_hash != config_hash
        ):
            config_changed = True
            change_reasons.append(f"configuration hash changed")

        # If config changed, recreate the task
        if config_changed:
            logger.info(
                "Configuration changed, updating task", 
                token=token, 
                reasons=change_reasons
            )
            
            # Create a new task function with updated config
            task_function = create_task_for_token(token)
            tasks[token] = task_function

            task_id = f"task_{token}"
            time_delta = int(config["configt"]["time_delta"])

            # Reschedule with new function and time_delta
            if scheduler.get_job(task_id):
                scheduler.remove_job(task_id)

            scheduler.add_job(
                task_function,
                "interval",
                seconds=time_delta,
                id=task_id,
                replace_existing=True,
            )
            
            logger.info(
                "Task updated with new configuration", 
                token=token, 
                task_id=task_id,
                time_delta=time_delta
            )

            # Update stored values
            tasks[token].time_delta = time_delta
            tasks[token].config_hash = config_hash
        else:
            logger.debug("No configuration changes detected", token=token)

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
