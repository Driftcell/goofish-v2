import asyncio
import json
import os

from minio import Minio
from playwright.async_api import async_playwright

from ai import AIUtils, GoodsManager
from api.agiso import AgisoApi
from api.ctrip import CtripApi
from db import MongoDB
from helpers.agiso import AgisoLoginHelper
from helpers.base import LoginState
from helpers.ctrip import CtripLoginHelper
from helpers.goofish import GoofishLoginHelper
from im import GoofishIM


async def main():
    MongoDB(os.getenv("MONGO_URI", ""), os.getenv("MONGO_DB", ""))

    minio_client = Minio(
        endpoint=os.getenv("MINIO_ENDPOINT"),  # type: ignore
        access_key=os.getenv("MINIO_ACCESS_KEY"),
        secret_key=os.getenv("MINIO_SECRET_KEY"),
        secure=False,  # 如果是 http 则设置为 False
    )

    async with async_playwright() as p:
        loginHelper = AgisoLoginHelper(
            playwright=p,
        )

        with open("cookies/agiso.json") as f:
            cookies = json.load(f)

        cookies = cookies["cookies"]

        await loginHelper.init(cookies=cookies)
        # await loginHelper.login("cookies/agiso.json")

        while await loginHelper.check_login_state() != LoginState.LOGINED:
            await asyncio.sleep(1)

        await loginHelper.save_cookies("cookies/agiso.json")

        cookies = await loginHelper.get_cookies()
        cookies = [{"name": cookie.get("name"), "value": cookie.get("value")} for cookie in cookies]
        api = AgisoApi(cookies=cookies, token=await loginHelper.get_token(), minio=minio_client)

        item = await MongoDB.get_db().items.find_one()
        await api.upload_item(item)

        # await loginHelper.init(headless=False, cookies=cookies)

        # while await loginHelper.check_login_state() != LoginState.LOGINED:
        #     await asyncio.sleep(1)

        # cookies = await loginHelper.get_cookies()

        # im = GoofishIM(db=MongoDB.get_db(), playwright=p, cookies=cookies)

        # await im.init()

        # await asyncio.sleep(5)

        # await im.start()

        # await asyncio.sleep(100000)


if __name__ == "__main__":
    asyncio.run(main())
