from urllib.parse import parse_qs, urlparse

import structlog
from playwright.async_api import Playwright

from .base import LoginHelper, LoginState
from .error import LoginHelperError

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class CtripLoginHelper(LoginHelper):
    """
    携程（Ctrip）登录助手类，用于管理携程登录相关的操作。
    继承自基础登录助手类 LoginHelper。
    """
    def __init__(self, playwright: Playwright, entrypoint: str) -> None:
        """
        初始化携程登录助手。
        
        Args:
            playwright (Playwright): Playwright 实例，用于浏览器自动化
            entrypoint (str): 携程登录后的入口点 URL
        """
        super().__init__(playwright)
        self._entrypoint = entrypoint

    async def init(self, headless: bool = False, *, cookies=None):
        """
        初始化浏览器上下文并导航到携程联盟页面。
        
        Args:
            headless (bool, optional): 是否以无头模式运行浏览器。默认为 False
            cookies (list, optional): 用于认证的 cookies。如果提供，将添加到浏览器上下文中
        """
        await super().init(headless)

        if cookies is not None:
            await self._context.add_cookies(cookies)

        await self._page.goto(
            "https://u.ctrip.com/alliance/#/CooperationModel/HotelPresale",
            wait_until="networkidle",
        )

    async def check_login_state(self):
        """
        检查当前登录状态。
        
        Returns:
            LoginState: 返回登录状态枚举值，LOGINED 表示已登录，UNLOGINED 表示未登录
        
        Note:
            通过检查当前 URL 是否以初始化时提供的 entrypoint 开头来判断登录状态
        """
        self._check_initialized()
        
        if self._page.url.startswith(self._entrypoint):
            return LoginState.LOGINED
        else:
            return LoginState.UNLOGINED

    def sid(self):
        """
        获取 URL 中的会话 ID (sid) 参数值。
        
        Returns:
            str: 当前页面 URL 中的 sid 参数值
        
        Note:
            使用 urlparse 和 parse_qs 从当前页面 URL 中提取 sid 参数
        """
        self._check_initialized()

        qs = parse_qs(urlparse(self._page.url, allow_fragments=False).query)
        return qs.get("sid", [])[0]

    def alliance_id(self):
        """
        获取 URL 中的联盟 ID (allianceId) 参数值。
        
        Returns:
            str: 当前页面 URL 中的 allianceId 参数值
        
        Note:
            使用 urlparse 和 parse_qs 从当前页面 URL 中提取 allianceId 参数
        """
        self._check_initialized()

        qs = parse_qs(urlparse(self._page.url, allow_fragments=False).query)
        return qs.get("allianceId", [])[0]
