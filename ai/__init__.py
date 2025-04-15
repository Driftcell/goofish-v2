import os
import re
from hashlib import md5
from tkinter import N

import structlog
from aiocache import cached
from aiohttp import ClientSession
from motor.motor_asyncio import AsyncIOMotorDatabase

from db import MongoDB
from templates import Template

from .error import AiUtilsError

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class AIUtils:
    """
    AI工具类，用于处理与人工智能相关的操作，主要与百度AI服务交互。
    """
    
    @cached(ttl=60 * 10)
    @staticmethod
    async def _get_access_token():
        """
        从百度OAuth服务获取访问令牌
        
        令牌会被缓存10分钟，以避免频繁API调用
        
        返回:
            str: 百度AI API的访问令牌
            
        异常:
            AiUtilsError: 如果令牌获取失败
        """
        url = "https://aip.baidubce.com/oauth/2.0/token"
        # 设置请求参数
        params = {
            "grant_type": "client_credentials",
            "client_id": os.getenv("BAIDU_API_KEY"),
            "client_secret": os.getenv("BAIDU_SECRET_KEY"),
        }
        async with ClientSession() as session:
            async with session.post(url, params=params) as response:
                data = await response.json()

                token = data.get("access_token")
                # 检查是否成功获取令牌
                if token is None:
                    raise AiUtilsError(
                        response.status,
                        "Failed to get access token from baidu oauth service",
                    )

                return token

    @staticmethod
    async def generate_title(
        title: str, description: str, price: float, *, template_text: str | None = None
    ):
        """
        使用百度AI服务生成优化的产品标题
        
        参数:
            title (str): 原始产品标题/名称
            description (str): 产品描述文本
            price (float): 产品价格
            template_text (str, optional): 自定义模板字符串，如果为None，则从数据库获取模板
        
        返回:
            str: AI生成的优化产品标题
        """
        # 获取百度API的授权令牌
        token = await AIUtils._get_access_token()
        url = os.getenv("BAIDU_API_URL") + token

        # 准备提示模板
        if template_text is None:
            template = Template(MongoDB.get_db())
            prompt = await template.get("prompt")
            prompt = prompt.format(title=title, description=description, price=price)
        else:
            prompt = template_text.format(
                title=title, description=description, price=price
            )

        data = {"messages": [{"role": "user", "content": prompt}]}

        async with ClientSession() as session:
            async with session.post(url, json=data) as response:
                data = await response.json()

                return data["result"]


class GoodsManager:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def merge_all(self, *, template: str | None = None):
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
                    title=subName,
                    description=copywriterInfo,
                    price=price,
                    template_text=template,
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
