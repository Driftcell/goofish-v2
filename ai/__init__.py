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
        从百度OAuth服务获取访问令牌。

        令牌会被缓存10分钟，以避免频繁API调用。

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
                        "无法从百度OAuth服务获取访问令牌",
                    )

                return token

    @staticmethod
    async def generate_title(
        title: str, description: str, price: float, *, template_text: str | None = None
    ):
        """
        使用百度AI服务生成优化的产品标题。

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

        # 调用百度AI服务生成标题
        async with ClientSession() as session:
            async with session.post(url, json=data) as response:
                data = await response.json()

                return data["result"]


class GoodsManager:
    """
    商品管理类，负责商品数据的聚合与处理。
    """
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """
        初始化方法。

        参数:
            db (AsyncIOMotorDatabase): MongoDB数据库实例
        """
        self._db = db

    async def merge_all(self, *, template: str | None = None):
        """
        聚合所有商品数据，并生成优化后的商品信息。

        参数:
            template (str, optional): 自定义AI提示模板

        返回:
            None
        """
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

        # 遍历聚合后的商品分组
        async for group in self._db.goods.aggregate(pipeline):
            # 获取原始商品ID列表，并排序
            originalProductId = sorted([item["productId"] for item in group["items"]])

            # 生成唯一的商品ID
            productId = md5("".join(originalProductId).encode("utf-8")).hexdigest()
            # 处理图片列表，仅保留文件名部分
            imgList = [image.split("/")[-1] for image in group["items"][0]["imgList"]]
            price = group["price"]
            subName = group["_id"]

            # 构建短链接及描述信息列表
            shortUrls = [
                {"shortUrl": item["shortUrl"], "description": item["productName"]}
                for item in group["items"]
            ]
            # 获取商品文案信息，并去除'-'字符
            copywriterInfo = group["items"][0]["copywriterInfo"][0][
                "copywriter"
            ].replace("-", "")

            # 获取商品结束销售时间，并提取日期
            endSaleTimeDesc = group["items"][0]["endSaleTimeDesc"]
            endSaleTimeDesc = re.search(r"\d{4}-\d{2}-\d{2}", endSaleTimeDesc)
            assert endSaleTimeDesc is not None
            endSaleTimeDesc = endSaleTimeDesc.group()

            try:
                # 调用AI生成商品标题
                title = await AIUtils.generate_title(
                    title=subName,
                    description=copywriterInfo,
                    price=price,
                    template_text=template,
                )
            except Exception as e:
                logger.warn(f"生成标题失败，原因：{e}")
                continue

            logger.info(f"为商品{productId}生成标题：{title}")

            # 更新或插入商品信息到items集合
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
