from typing import Literal

from motor.motor_asyncio import AsyncIOMotorDatabase
from playwright.async_api import async_playwright

from helpers.agiso import AgisoLoginHelper
from helpers.base import LoginState
from helpers.ctrip import CtripLoginHelper
from helpers.goofish import GoofishLoginHelper


async def build_config(token: str, db: AsyncIOMotorDatabase):
    """
    构建用户配置
    
    根据用户token从数据库中获取并组装用户的所有配置项。
    
    Args:
        token (str): 用户认证令牌
        db (AsyncIOMotorDatabase): 数据库连接
        
    Returns:
        dict: 包含所有用户配置的字典，键为配置名称，值为配置内容
    """
    config = db.configs.find({"token": token})
    built_config = {}

    async for item in config:
        built_config[item["name"]] = item["value"]

    return built_config


async def check_login(
    platform: Literal["goofish", "agiso", "ctrip"], cookies, *, headless=False
) -> bool:
    """
    检查平台登录状态
    
    使用提供的cookies检查指定平台的登录状态是否有效。
    
    Args:
        platform (Literal["goofish", "agiso", "ctrip"]): 平台名称
        cookies: 平台的cookie信息
        headless (bool, optional): 是否以无头模式运行浏览器，默认为False
        
    Returns:
        bool: 登录状态是否有效
        
    Raises:
        ValueError: 当提供不支持的平台名称时抛出
    """
    async with async_playwright() as p:
        match platform:
            case "goofish":
                loginHelper = GoofishLoginHelper(playwright=p)
            case "agiso":
                loginHelper = AgisoLoginHelper(playwright=p)
            case "ctrip":
                loginHelper = CtripLoginHelper(
                    playwright=p,
                    entrypoint="https://u.ctrip.com/alliance/#/CooperationModel/HotelPresale",
                )
            case _:
                raise ValueError("Unsupported platform")

        await loginHelper.init(cookies=cookies, headless=headless)
        return await loginHelper.check_login_state() == LoginState.LOGINED
