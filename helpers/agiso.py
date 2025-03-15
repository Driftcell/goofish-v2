from pathlib import Path
import structlog
from playwright.async_api import Playwright

from .goofish import GoofishLoginHelper

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class AgisoLoginHelper(GoofishLoginHelper):
    def __init__(self, playwright: Playwright):
        super().__init__(playwright)

    async def login(self, path: Path | str | None = None):
        return await super().login(path=path)

    async def save_cookies(self, path: Path | str):
        self._check_initialized()

        await self._goto_agiso()
        await self._context.storage_state(path=path)

    async def get_token(self):
        self._check_initialized()

        await self._goto_agiso()
        return await self._page.evaluate("localStorage.getItem('TOKEN')")

    async def get_cookies(self):
        self._check_initialized()

        await self._goto_agiso()
        return await self._context.cookies()

    async def _goto_agiso(self):
        url = "https://aldsidle.agiso.com/#/goodsManage/goodsList"
        await self._page.goto(
            url,
            wait_until="networkidle",
        )
