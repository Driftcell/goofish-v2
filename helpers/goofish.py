from pathlib import Path

import structlog
from playwright.async_api import Playwright

from .base import LoginHelper, LoginState
from .error import LoginHelperError

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class GoofishLoginHelper(LoginHelper):
    def __init__(self, playwright: Playwright):
        super().__init__(playwright)

    async def init(self, headless: bool = False, *, cookies = None):
        await super().init(headless, cookies=cookies)

        await self._page.goto("https://www.goofish.com/", wait_until="networkidle")

    async def login(self, path: Path | str | None = None):
        self._check_initialized()

        await self._click_login_button()
        return await self._save_QRCode(path)

    async def check_login_state(self):
        if await self._page.locator("[class^='nick-']").text_content() == "登录":
            return LoginState.UNLOGINED
        else:
            return LoginState.LOGINED

    async def _click_keep_login_button(self):
        locator = "#login > div.extra-login-content > div > div.login-blocks.block4 > div.keep-login-confirm.show > div > div > div.keep-login-confirm-footer > button.fm-button.fm-submit.keep-login-btn.keep-login-confirm-btn.primary"
        frame = self._page.frame_locator("#alibaba-login-box")
        await frame.locator(locator).click()

    async def _click_login_button(self):
        locator = "#ice-container > div.bottomLead--aH0Oblol > div > div"

        try:
            await self._page.locator(locator).click()
        except Exception as e:
            raise LoginHelperError(f"_click_login_button error: {e}")

        await self._page.wait_for_load_state("networkidle")

    async def _save_QRCode(self, path: Path | str | None):
        frame = self._page.frame_locator("#alibaba-login-box")
        qrcode = frame.locator("#login > div.extra-login-content > div")

        try:
            return await qrcode.screenshot(path=path)
        except Exception as e:
            raise LoginHelperError(f"_save_QRCode error: {e}")
