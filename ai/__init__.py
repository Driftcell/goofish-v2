import os
import re
from hashlib import md5

import structlog
from aiocache import cached
from aiohttp import ClientSession
from motor.motor_asyncio import AsyncIOMotorDatabase

from db import MongoDB
from templates import Template

from .error import AiUtilsError

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class AIUtils:
    @cached(ttl=60 * 10)
    @staticmethod
    async def _get_access_token():
        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": os.getenv("BAIDU_API_KEY"),
            "client_secret": os.getenv("BAIDU_SECRET_KEY"),
        }
        async with ClientSession() as session:
            async with session.post(url, params=params) as response:
                data = await response.json()

                token = data.get("access_token")
                if token is None:
                    raise AiUtilsError(
                        response.status,
                        "Failed to get access token from baidu oauth service",
                    )

                return token

    @staticmethod
    async def generate_title(title: str, description: str, price: float):
        token = await AIUtils._get_access_token()
        url = os.getenv("BAIDU_API_URL") + token
        template = Template(MongoDB.get_db())
        prompt = await template.get("prompt")

        prompt = prompt.format(title=title, description=description, price=price)

        data = {"messages": [{"role": "user", "content": prompt}]}

        async with ClientSession() as session:
            async with session.post(url, json=data) as response:
                data = await response.json()

                return data["result"]


class GoodsManager:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def merge_all(self):
        pipeline = [
            {
                "$group": {
                    "_id": "$subName",
                    "count": {"$sum": 1},
                    "price": {"$min": "$price"},
                    "items": {"$push": "$$ROOT"},
                }
            }
        ]

        async for group in self._db.goods.aggregate(pipeline):
            originalProductId = sorted([item["productId"] for item in group["items"]])

            productId = md5("".join(originalProductId).encode("utf-8")).hexdigest()
            imgList = [image.split("/")[-1] for image in group["items"][0]["imgList"]]
            price = group["price"]
            subName = group["_id"]

            shortUrls = [
                {"shortUrl": item["shortUrl"], "description": item["productName"]}
                for item in group["items"]
            ]
            copywriterInfo = group["items"][0]["copywriterInfo"][0][
                "copywriter"
            ].replace("-", "")

            # End sale time
            endSaleTimeDesc = group["items"][0]["endSaleTimeDesc"]
            endSaleTimeDesc = re.search(r"\d{4}-\d{2}-\d{2}", endSaleTimeDesc)
            assert endSaleTimeDesc is not None
            endSaleTimeDesc = endSaleTimeDesc.group()

            try:
                title = await AIUtils.generate_title(
                    title=subName, description=copywriterInfo, price=price
                )
            except Exception as e:
                logger.warn(f"Failed to generate title due to {e}")
                continue

            logger.info(f"Generated title {title} for {productId}")

            await self._db.items.update_one(
                {"productId": productId},
                {
                    "$set": {
                        "originalProductId": originalProductId,
                        "title": title,
                        "imgList": imgList,
                        "price": price,
                        "subName": subName,
                        "shortUrls": shortUrls,
                        "copywriterInfo": copywriterInfo,
                        "endSaleTimeDesc": endSaleTimeDesc,
                    }
                },
                upsert=True,
            )
