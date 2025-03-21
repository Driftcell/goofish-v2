import argparse
import asyncio
import os

import structlog
from playwright.async_api import async_playwright

from helpers.base import LoginState
from helpers.ctrip import CtripLoginHelper
from helpers.goofish import GoofishLoginHelper

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


async def ctrip():
    logger.info("Starting Ctrip login process")
    async with async_playwright() as p:
        logger.debug("Initializing Ctrip login helper")
        loginHelper = CtripLoginHelper(
            playwright=p,
            entrypoint="https://u.ctrip.com/alliance/#/CooperationModel/HotelPresale",
        )
        await loginHelper.init()

        logger.info("Waiting for user to login")
        while await loginHelper.check_login_state() != LoginState.LOGINED:
            await asyncio.sleep(1)

        logger.info("Login successful, saving cookies")
        os.makedirs("cookies", exist_ok=True)
        await loginHelper.save_cookies("cookies/ctrip.json")
        logger.info("Ctrip cookies saved successfully")


async def goofish():
    logger.info("Starting Goofish login process")
    async with async_playwright() as p:
        logger.debug("Initializing Goofish login helper")
        loginHelper = GoofishLoginHelper(
            playwright=p,
        )
        await loginHelper.init()
        await loginHelper.login()

        logger.info("Waiting for user to login")
        while await loginHelper.check_login_state() != LoginState.LOGINED:
            await asyncio.sleep(1)

        logger.info("Login successful, saving cookies")
        os.makedirs("cookies", exist_ok=True)
        await loginHelper.save_cookies("cookies/goofish.json")
        logger.info("Goofish cookies saved successfully")


async def main():
    parser = argparse.ArgumentParser(description="CLI tool for login")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("ctrip", help="Run ctrip command")
    subparsers.add_parser("goofish", help="Run goofish command")

    args = parser.parse_args()

    if args.command == "ctrip":
        await ctrip()
    elif args.command == "goofish":
        await goofish()


if __name__ == "__main__":
    asyncio.run(main())
