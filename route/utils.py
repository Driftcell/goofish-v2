from typing import Literal

from playwright.async_api import async_playwright

from helpers.agiso import AgisoLoginHelper
from helpers.base import LoginState
from helpers.ctrip import CtripLoginHelper
from helpers.goofish import GoofishLoginHelper


async def check_login(platform: Literal["goofish", "agiso", "ctrip"], cookies) -> bool:
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

        await loginHelper.init(cookies=cookies)
        return await loginHelper.check_login_state() == LoginState.LOGINED
