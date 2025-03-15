from itertools import product

import structlog
from minio import Minio
from motor.motor_asyncio import AsyncIOMotorDatabase
from playwright.async_api import async_playwright

from ai import GoodsManager
from api import agiso, ctrip
from api.agiso import AgisoApi
from api.ctrip import CtripApi
from helpers.agiso import AgisoLoginHelper
from helpers.ctrip import CtripLoginHelper

from .utils import check_login

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

tasks = {}

async def run(token: str, config, db: AsyncIOMotorDatabase, minio: Minio):
    user = await db.users.find_one({"token": token})

    if not user:
        raise ValueError("User not found")

    ctrip_cookies = user["ctrip"]
    agiso_cookies = user["agiso"]

    if not await check_login(platform="ctrip", cookies=ctrip_cookies):
        raise ValueError("User not logged in")
    async with async_playwright() as p:
        ctrip_login_helper = CtripLoginHelper(
            playwright=p,
            entrypoint="https://u.ctrip.com/alliance/#/CooperationModel/HotelPresale",
        )

        await ctrip_login_helper.init(cookies=ctrip_cookies)
        alliance_id = ctrip_login_helper.alliance_id()
        sid = ctrip_login_helper.sid()

    ctrip_cookies = [
        {"name": cookie.get("name"), "value": cookie["value"]}
        for cookie in ctrip_cookies
    ]
    ctrip_api = CtripApi(
        cookies=ctrip_cookies,
        db=db,
        minio=minio,
        alliance_id=alliance_id,
        sid=sid,
    )

    # 爬虫
    await ctrip_api.run("上海")
    # 合并商品
    template = config["template"]["value"]["template"]
    await GoodsManager(db).merge_all(template=template)

    # 上传商品
    async with async_playwright() as p:
        agiso_login_helper = AgisoLoginHelper(playwright=p)
        await agiso_login_helper.init()
        token = await agiso_login_helper.get_token()

    agiso_cookies = [
        {"name": cookie.get("name"), "value": cookie["value"]}
        for cookie in agiso_cookies
    ]
    agiso_api = AgisoApi(cookies=agiso_cookies, minio=minio, token=token)

    # 已经上传的不要上传
    uploaded_goods = await agiso_api.search_good_list()
    uploaded_set = set()
    for uploaded in uploaded_goods:
        if id := uploaded.get("outerGoodsId"):
            uploaded_set.add(id)

    uploaded_count = len(uploaded_goods)
    items = db.items.find()

    async for item in items:
        # 检查商品是否已经上传
        if item["productId"] in uploaded_set:
            logger.info(f"Already uploaded, skip", productId=item["productId"])
            continue
        
        # 应用过滤器
        filters = item["filter"]["keywords_filter"]
        if item["filter"]["keywords_filter_enabled"] and filters:
            for keyword in filters:
                if keyword in item["subName"] + item["copywriterInfo"] + item["title"]:
                    logger.info(
                        f"Product name match filter, skip", productId=item["productId"]
                    )
                    break

        # 应用价格过滤器
        limits = config["configts"]["item_limits"]
        if uploaded_count >= limits:
            logger.info(f"Reached the limits, stopping", limits=limits)
            break

        try:
            await agiso_api.upload_item(
                item,
                draft=False,
                price_mode=config["configt"]["price"]["mode"],
                price=config["configt"]["price"]["value"],
            )
            uploaded_count += 1
            logger.info(f"Uploaded item", productId=item["productId"])
        except Exception as e:
            logger.warn(
                f"Failed to upload production",
                productId=item["productId"],
                error=str(e),
            )
