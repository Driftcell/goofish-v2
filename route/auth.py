import json
from hashlib import md5

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from .depends import get_db

router = APIRouter(tags=["auth"])


@router.post("/login")
async def p_login(
    goofish: UploadFile = File(...),
    ctrip: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    goofish_bytes = await goofish.read()
    agiso_bytes = await ctrip.read()

    token = md5(goofish_bytes + agiso_bytes).hexdigest()

    goofish_json = json.loads(goofish_bytes.decode("utf-8"))
    agiso_json = json.loads(agiso_bytes.decode("utf-8"))
    await db.users.update_one(
        {"token": token},
        {"$set": {"goofish": goofish_json, "agiso": agiso_json}},
        upsert=True,
    )

    return JSONResponse({"code": 0, "message": "ok", "data": {"token": token}})
