from urllib.parse import parse_qs, urlparse

import structlog
from playwright.async_api import Playwright

from .base import LoginHelper, LoginState
from .error import LoginHelperError

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class CtripLoginHelper(LoginHelper):
    def __init__(self, playwright: Playwright, entrypoint: str) -> None:
        super().__init__(playwright)
        self._entrypoint = entrypoint

    async def init(self, headless: bool = False, *, cookies=None):
        await super().init(headless)

        if cookies is not None:
            await self._context.add_cookies(cookies)

        await self._page.goto(
            "https://u.ctrip.com/alliance/#/CooperationModel/HotelPresale",
            wait_until="networkidle",
        )

    async def check_login_state(self):
        self._check_initialized()
        
        if self._page.url.startswith(self._entrypoint):
            return LoginState.LOGINED
        else:
            return LoginState.UNLOGINED

    def sid(self):
        self._check_initialized()

        qs = parse_qs(urlparse(self._page.url, allow_fragments=False).query)
        return qs.get("sid", [])[0]

    def alliance_id(self):
        self._check_initialized()

        qs = parse_qs(urlparse(self._page.url, allow_fragments=False).query)
        return qs.get("allianceId", [])[0]
