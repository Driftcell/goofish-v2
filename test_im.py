import asyncio
import json
import os

from playwright.async_api import async_playwright

from db import MongoDB
from helpers.base import LoginState
from helpers.goofish import GoofishLoginHelper


async def main():
    MongoDB(os.getenv("MONGO_URI", ""), os.getenv("MONGO_DB", ""))

    async with async_playwright() as p:
        login_helper = GoofishLoginHelper(p)

        with open("cookies/goofish.json", "r") as f:
            cookies = json.loads(f.read())['cookies']

        await login_helper.init(cookies=cookies)
        # await login_helper.login()

        while await login_helper.check_login_state() != LoginState.LOGINED:
            await asyncio.sleep(1)

        cookies = await login_helper.get_cookies()

    async with async_playwright() as p:
        from im import GoofishIM

        goofish_im = GoofishIM(
            playwright=p, cookies=cookies, db=MongoDB.get_db()
        )

        await goofish_im.init()
        await goofish_im.start()

        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            await goofish_im.stop()


if __name__ == "__main__":
    asyncio.run(main())
