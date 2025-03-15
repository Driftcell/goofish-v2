import json
from asyncio import gather
from hashlib import md5

import structlog
from fastapi import APIRouter, Depends, File, UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase

from route.types import ErrorResponse, MyResponse

from .depends import get_db
from .utils import check_login

router = APIRouter(tags=["auth"])

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


@router.post("/login")
async def p_login(
    goofish: UploadFile = File(...),
    ctrip: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    goofish_bytes = await goofish.read()
    ctrip_bytes = await ctrip.read()

    token = md5(goofish_bytes + ctrip_bytes).hexdigest()

    goofish_json: dict = json.loads(goofish_bytes.decode("utf-8"))
    ctrip_json: dict = json.loads(ctrip_bytes.decode("utf-8"))

    goofish_login = await check_login("goofish", goofish_json["cookies"])
    ctrip_login = await check_login("ctrip", ctrip_json["cookies"])

    logger.info(
        "login",
        goofish=goofish_login,
        ctrip=ctrip_login,
        token=token,
    )

    if not goofish_login or isinstance(goofish_login, Exception):
        return ErrorResponse(code=1, message="Goofish login failed", data=None)
    if not ctrip_login or isinstance(ctrip_login, Exception):
        return ErrorResponse(code=1, message="Agiso login failed", data=None)

    await db.users.update_one(
        {"token": token},
        {"$set": {"goofish": goofish_json, "ctrip": ctrip_json}},
        upsert=True,
    )

    return MyResponse(code=0, message="Login successful", data={"token": token})
