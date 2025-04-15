import argparse
import asyncio
import os

import structlog
from playwright.async_api import async_playwright

from helpers.base import LoginState
from helpers.ctrip import CtripLoginHelper
from helpers.goofish import GoofishLoginHelper

# 获取结构化日志记录器
logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


async def ctrip():
    """
    携程登录处理函数。
    
    该异步函数使用 Playwright 自动化浏览器操作，引导用户登录携程商家平台。
    登录成功后，会保存用户的 cookies 到本地文件系统，以便后续请求使用。
    
    Returns:
        None
    """
    logger.info("Starting Ctrip login process")
    async with async_playwright() as p:
        logger.debug("Initializing Ctrip login helper")
        # 初始化携程登录助手，指定入口点URL
        loginHelper = CtripLoginHelper(
            playwright=p,
            entrypoint="https://u.ctrip.com/alliance/#/CooperationModel/HotelPresale",
        )
        await loginHelper.init()

        logger.info("Waiting for user to login")
        # 循环检查登录状态，直到用户成功登录
        while await loginHelper.check_login_state() != LoginState.LOGINED:
            await asyncio.sleep(1)

        logger.info("Login successful, saving cookies")
        # 确保cookies目录存在
        os.makedirs("cookies", exist_ok=True)
        # 保存cookies到指定文件
        await loginHelper.save_cookies("cookies/ctrip.json")
        logger.info("Ctrip cookies saved successfully")


async def goofish():
    """
    咸鱼平台登录处理函数。
    
    该异步函数使用 Playwright 自动化浏览器操作，引导用户登录咸鱼平台。
    登录成功后，会保存用户的 cookies 到本地文件系统，以便后续请求使用。
    
    Returns:
        None
    """
    logger.info("Starting Goofish login process")
    async with async_playwright() as p:
        logger.debug("Initializing Goofish login helper")
        # 初始化咸鱼登录助手
        loginHelper = GoofishLoginHelper(
            playwright=p,
        )
        await loginHelper.init()
        await loginHelper.login()

        logger.info("Waiting for user to login")
        # 循环检查登录状态，直到用户成功登录
        while await loginHelper.check_login_state() != LoginState.LOGINED:
            await asyncio.sleep(1)

        logger.info("Login successful, saving cookies")
        # 确保cookies目录存在
        os.makedirs("cookies", exist_ok=True)
        # 保存cookies到指定文件
        await loginHelper.save_cookies("cookies/goofish.json")
        logger.info("Goofish cookies saved successfully")


async def main():
    """
    CLI工具的主函数，处理命令行参数并执行相应的操作。
    
    该函数解析命令行参数，根据用户输入的子命令调用对应的登录处理函数。
    目前支持 'ctrip' 和 'goofish' 两个子命令。
    
    Returns:
        None
    """
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="CLI tool for login")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 添加子命令
    subparsers.add_parser("ctrip", help="Run ctrip command")
    subparsers.add_parser("goofish", help="Run goofish command")

    # 解析命令行参数
    args = parser.parse_args()

    # 根据子命令执行相应函数
    if args.command == "ctrip":
        await ctrip()
    elif args.command == "goofish":
        await goofish()


if __name__ == "__main__":
    # 程序入口点，运行主异步函数
    asyncio.run(main())
