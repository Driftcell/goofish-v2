from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from .depends import get_db, get_token
from .types import Config, ConfigT, MyResponse

router = APIRouter(tags=["config"])


@router.get("/config/{name}", response_model=MyResponse[Any])
async def g_config(
    name: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    token: str = Depends(get_token),
):
    config = await db.configs.find_one({"name": name, "token": token})

    presets = ["filter", "configt", "template", "description", "reply", "report"]

    if config:
        return MyResponse(data=config.get("value"))

    if name not in presets:
        raise HTTPException(404, f"Not found such key: {name}")

    else:
        match name:
            case "filter":
                await db.configs.insert_one(
                    {
                        "token": token,
                        "name": "filter",
                        "value": {
                            "keywords_filter_enabled": False,
                            "keywords_filter": [],
                        },
                    }
                )
            case "configt":
                await db.configs.insert_one(
                    {
                        "token": token,
                        "name": "configt",
                        "value": {
                            "time_delta": "3000",
                            "item_limits": "3000",
                            "price": {"mode": "fixed", "value": "1"},
                            "item_type": "家居/服务/跑腿代办/酒店代订",
                        },
                    }
                )
            case "template":
                await db.configs.insert_one(
                    {
                        "token": token,
                        "name": "template",
                        "value": {
                            "template": "根据要求和信息，写一句话。\n# 使用短句。\n# 直接回答，不要出现其他话。\n# 先突出价格，向下取整。有多天的价格就把价格算成一天的。\n# 再突出地点。\n# 然后有品牌突出品牌。\n少于20个字\n####信息####\n{title}\n{description}\n{price}元\n##例子##\n600悦榕庄！九寨沟悦榕庄！送餐饮!行政酒廊！\n400五星级套房！成都上层名人酒店!"
                        },
                    }
                )
            case "description":
                await db.configs.insert_one(
                    {
                        "token": token,
                        "name": "description",
                        "value": {"template": "{goods_information}"},
                    }
                )
            case "reply":
                await db.configs.insert_one(
                    {
                        "token": token,
                        "name": "reply",
                        "value": {"template": ""},
                    }
                )
            case "report":
                await db.configs.insert_one(
                    {
                        "token": token,
                        "name": "report",
                        "value": {"email": "3392677391@qq.com"},
                    }
                )

        config = await db.configs.find_one(
            {
                "name": name,
                "token": token,
            }
        )
        assert config is not None
        return MyResponse(data=config.get("value"))


@router.post("/config")
async def p_config(
    config: Config,
    db: AsyncIOMotorDatabase = Depends(get_db),
    token: str = Depends(get_token),
):
    await db.configs.update_one(
        {"name": config.name, "token": token},
        update={"$set": {"value": config.value, "token": token}},
        upsert=True,
    )

    return {"code": 0, "message": "Updated"}


@router.post("/configt")
async def p_configt(
    config: ConfigT,
    db: AsyncIOMotorDatabase = Depends(get_db),
    token: str = Depends(get_token),
):
    await db.configs.update_one(
        {"name": "configt", "token": token},
        {"$set": {"value": config.model_dump(), "token": token}},
        upsert=True,
    )

    return {"code": 0, "message": "ok"}


@router.get("/configt", response_model=MyResponse[ConfigT])
async def g_configt(
    db: AsyncIOMotorDatabase = Depends(get_db), token: str = Depends(get_token)
):
    config = await db.configs.find_one({"name": "configt", "token": token})
    if not config:
        await db.configs.update_one(
            {"name": "configt"},
            {
                "$set": {
                    "value": ConfigT().model_dump(),
                    "token": token,
                }
            },
            upsert=True,
        )
        config = await db.configs.find_one(
            {
                "name": "configt",
                "token": token,
            }
        )
        assert config is not None

    config = config["value"]
    return MyResponse(data=ConfigT.model_validate(config))
