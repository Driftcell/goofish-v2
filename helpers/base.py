from enum import Enum
from pathlib import Path

from playwright.async_api import Playwright

from .error import LoginHelperError


class LoginHelper:
    def __init__(self, playwright: Playwright):
        self._playwright = playwright
        self._initialized = False

    async def init(self, headless: bool = False, *, cookies=None):
        self._browser = await self._playwright.chromium.launch(headless=headless)
        self._context = await self._browser.new_context()

        if cookies is not None:
            await self._context.add_cookies(cookies)

        await self._context.add_init_script(path="stealth.min.js/stealth.min.js")
        self._page = await self._context.new_page()

        self._initialized = True

    async def get_cookies(self):
        self._check_initialized()

        return await self._context.cookies()

    async def save_cookies(self, path: Path | str):
        self._check_initialized()

        await self._context.storage_state(path=path)

    def _check_initialized(self):
        if not self._initialized:
            raise LoginHelperError("call the init() first")


class LoginState(Enum):
    UNLOGINED = 0
    LOGINED = 1
    AUTHNEEDED = 2
