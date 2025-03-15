import json
from asyncio import gather
from hashlib import md5

from fastapi import APIRouter, Depends, File, UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase

from route.types import ErrorResponse, MyResponse

from .depends import get_db
from .utils import check_login

router = APIRouter(tags=["auth"])


@router.post("/login")
async def p_login(
    goofish: UploadFile = File(...),
    ctrip: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    goofish_bytes = await goofish.read()
    ctrip_bytes = await ctrip.read()

    token = md5(goofish_bytes + ctrip_bytes).hexdigest()

    goofish_json = json.loads(goofish_bytes.decode("utf-8"))
    agiso_json = json.loads(ctrip_bytes.decode("utf-8"))

    goofish_login, agiso_login = await gather(
        check_login("goofish", goofish_json["cookies"]),
        check_login("agiso", agiso_json["cookies"]),
        return_exceptions=True,
    )

    if not goofish_login and isinstance(goofish_login, Exception):
        return ErrorResponse(code=1, message="Goofish login failed", data=None)
    if not agiso_login and isinstance(agiso_login, Exception):
        return ErrorResponse(code=1, message="Agiso login failed", data=None)

    await db.users.update_one(
        {"token": token},
        {"$set": {"goofish": goofish_json, "agiso": agiso_json}},
        upsert=True,
    )

    return MyResponse(code=0, message="Login successful", data={"token": token})
