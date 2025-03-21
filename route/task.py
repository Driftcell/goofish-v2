import asyncio
from typing import Any, Dict

import structlog
from minio import Minio
from motor.motor_asyncio import AsyncIOMotorDatabase
from playwright.async_api import async_playwright

from ai import GoodsManager
from api.agiso import AgisoApi
from api.ctrip import CtripApi
from db import MongoDB
from helpers.agiso import AgisoLoginHelper
from helpers.base import LoginState
from helpers.ctrip import CtripLoginHelper
from im import GoofishIM

from .utils import build_config, check_login

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

# Dictionary to store token-specific task functions
tasks = {}

# Dictionary to store im_tasks
im_tasks: Dict[str, Dict[str, Any]] = {}


# Function to create a task for a specific token
def create_task_for_token(token: str):
    async def task_function():
        # Get database and minio client
        db = MongoDB.get_db()

        from .depends import get_minio

        minio = await get_minio()

        # Build config for the token
        config = await build_config(token, db)

        # Run the main function with the token, config, database and minio
        await run(token, config, db, minio)

    # Return the task function
    return task_function


async def run(token: str, config, db: AsyncIOMotorDatabase, minio: Minio):
    user = await db.users.find_one({"token": token})

    if not user:
        raise ValueError("User not found")

    ctrip_cookies = user["ctrip"]["cookies"]
    agiso_cookies = user["goofish"]["cookies"]

    if not await check_login(platform="ctrip", cookies=ctrip_cookies):
        raise ValueError("User not logged in")
    async with async_playwright() as p:
        ctrip_login_helper = CtripLoginHelper(
            playwright=p,
            entrypoint="https://u.ctrip.com/alliance/#/CooperationModel/HotelPresale",
        )

        await ctrip_login_helper.init(cookies=ctrip_cookies)

        if await ctrip_login_helper.check_login_state() != LoginState.LOGINED:
            await db.users.update_one(
                {"token": token},
                {"$set": {"expired": True}},
            )

            raise ValueError("Ctrip login failed")
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
    template = config["template"]["template"]
    await GoodsManager(db).merge_all(template=template)

    # 上传商品
    async with async_playwright() as p:
        agiso_login_helper = AgisoLoginHelper(playwright=p)
        await agiso_login_helper.init(cookies=agiso_cookies)

        if await agiso_login_helper.check_login_state() != LoginState.LOGINED:
            await db.users.update_one(
                {"token": token},
                {"$set": {"expired": True}},
            )
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
        if config["filter"]["keywords_filter_enabled"]:
            if filters := config["filter"]["keywords_filter"]:
                for keyword in filters:
                    if (
                        keyword
                        in item["subName"] + item["copywriterInfo"] + item["title"]
                    ):
                        logger.info(
                            f"Product name match filter, skip",
                            productId=item["productId"],
                        )
                        break

        # 应用价格过滤器
        limits = int(config["configt"]["item_limits"])
        if uploaded_count >= limits:
            logger.info(f"Reached the limits, stopping", limits=limits)
            break

        try:
            await agiso_api.upload_item(
                item,
                draft=False,
                price_mode=config["configt"]["price"]["mode"],
                price=config["configt"]["price"]["value"],
                template=config["description"]["template"],
            )
            uploaded_count += 1
            logger.info(f"Uploaded item", productId=item["productId"])
        except Exception as e:
            logger.warn(
                f"Failed to upload production",
                productId=item["productId"],
                error=str(e),
            )

        # 建立itemId和outerId的绑定
        items = await agiso_api.search_good_list()
        for item in items:
            db_item = await db.items.find_one({"productId": item["outerGoodsId"]})
            if db_item:
                await db.items.update_one(
                    {"productId": item["outerGoodsId"]},
                    {"$set": {"itemId": item["goodsId"]}},
                )


async def create_im_task(token: str, user: Dict[str, Any], db: AsyncIOMotorDatabase):
    """Create an IM task for a user if it doesn't exist already"""
    if token in im_tasks and im_tasks[token].get("running"):
        logger.debug(f"IM task already exists for token", token=token)
        return

    logger.info(f"Creating new IM task for user", token=token)

    im_tasks[token] = {"task": None, "running": False, "last_check": None}

    async def im_task_runner():
        logger.info(f"Starting IM task for user", token=token)
        im_tasks[token]["running"] = True

        try:
            cookies = user["goofish"]["cookies"]

            async with async_playwright() as p:
                im_client = GoofishIM(db=db, playwright=p, cookies=cookies, token=token)
                await im_client.init(cookies=cookies)
                await asyncio.sleep(5)
                await im_client.start()

                # Keep the task running indefinitely
                while True:
                    await asyncio.sleep(60)  # Sleep for 1 minute

                    # Check if user is still valid
                    current_user = await db.users.find_one({"token": token})
                    if not current_user or current_user.get("expired", False):
                        logger.info(
                            f"User expired or not found, stopping IM task", token=token
                        )
                        break

                await im_client.stop()

        except Exception as e:
            logger.exception(f"Error in IM task", token=token, error=str(e))
        finally:
            im_tasks[token]["running"] = False

    # Create the task but don't await it
    im_tasks[token]["task"] = asyncio.create_task(im_task_runner())
    return im_tasks[token]["task"]


async def check_and_create_im_tasks():
    """Check for non-expired users and create IM tasks for them"""
    # logger.info("Checking for non-expired users to create IM tasks")

    db = MongoDB.get_db()
    users = await db.users.find({"expired": False}).to_list()

    for user in users:
        token = user.get("token")
        if not token:
            continue

        await create_im_task(token, user, db)

    # logger.info(f"IM task check completed, active tasks: {sum(1 for t in im_tasks.values() if t.get('running'))}")


async def start_im_task_scheduler():
    """Start the scheduler that runs check_and_create_im_tasks every minute"""
    logger.info("Starting IM task scheduler")

    while True:
        try:
            await check_and_create_im_tasks()
        except Exception as e:
            logger.exception("Error checking IM tasks", error=str(e))

        await asyncio.sleep(5)  # Run every minute
