from typing import Any
from motor.motor_asyncio import AsyncIOMotorDatabase


class Template:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def get(self, name: str, default: Any = None) -> str | Any:
        result = await self._db.templates.find_one({"name": name})

        if not result:
            return default

        return result.get("value")

    async def set(self, name: str, value: str, *, upsert: bool = False):
        await self._db.templates.update_one(
            {"name": name}, {"$set": {"value": value}}, upsert=upsert
        )
