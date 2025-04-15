from pathlib import Path
import structlog
from playwright.async_api import Playwright

from .goofish import GoofishLoginHelper

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class AgisoLoginHelper(GoofishLoginHelper):
    """
    Agiso登录助手类，继承自GoofishLoginHelper，用于处理Agiso网站的登录、token和cookie相关操作。
    """
    def __init__(self, playwright: Playwright):
        """
        初始化AgisoLoginHelper实例。
        
        参数:
            playwright (Playwright): Playwright实例，用于浏览器自动化操作。
        """
        super().__init__(playwright)

    async def login(self, path: Path | str | None = None):
        """
        登录到Agiso系统。
        
        参数:
            path (Path | str | None, 可选): cookie存储路径，如果提供，将尝试使用保存的cookie登录。默认为None。
            
        返回:
            返回父类的登录结果。
        """
        return await super().login(path=path)

    async def save_cookies(self, path: Path | str):
        """
        保存当前会话的cookies到指定路径。
        
        参数:
            path (Path | str): 保存cookies的文件路径。
        """
        self._check_initialized()

        await self._goto_agiso()
        await self._context.storage_state(path=path)

    async def get_token(self):
        """
        获取当前会话的TOKEN。
        
        返回:
            str: 存储在localStorage中的TOKEN值。
        """
        self._check_initialized()

        await self._goto_agiso()
        return await self._page.evaluate("localStorage.getItem('TOKEN')")

    async def get_cookies(self):
        """
        获取当前会话的所有cookies。
        
        返回:
            list: 当前会话的cookies列表。
        """
        self._check_initialized()

        await self._goto_agiso()
        return await self._context.cookies()

    async def _goto_agiso(self):
        """
        内部方法，导航到Agiso商品管理页面。
        
        该方法会等待页面网络活动完成后再返回。
        """
        url = "https://aldsidle.agiso.com/#/goodsManage/goodsList"
        await self._page.goto(
            url,
            wait_until="networkidle",  # 等待网络活动完成
        )
