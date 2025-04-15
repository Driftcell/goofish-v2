from enum import Enum
from pathlib import Path

from playwright.async_api import Playwright

from .error import LoginHelperError


class LoginHelper:
    """
    登录助手类，用于处理网站登录相关操作。
    
    该类封装了使用 Playwright 进行网站登录的基本功能，
    包括浏览器初始化、Cookie 管理等操作。
    """
    
    def __init__(self, playwright: Playwright):
        """
        初始化登录助手。
        
        Args:
            playwright (Playwright): Playwright 实例对象
        """
        self._playwright = playwright
        self._initialized = False

    async def init(self, headless: bool = False, *, cookies=None):
        """
        初始化浏览器环境。
        
        Args:
            headless (bool, optional): 是否使用无头模式。默认为 False。
            cookies (list, optional): 要添加的 cookies 列表。默认为 None。
            
        Note:
            在使用其他方法前必须先调用此方法。
        """
        self._browser = await self._playwright.chromium.launch(headless=headless)
        self._context = await self._browser.new_context()

        if cookies is not None:
            await self._context.add_cookies(cookies)

        await self._context.add_init_script(path="stealth.min.js/stealth.min.js")
        self._page = await self._context.new_page()

        self._initialized = True

    async def get_cookies(self):
        """
        获取当前浏览器上下文的所有 cookies。
        
        Returns:
            list: Cookie 对象列表
            
        Raises:
            LoginHelperError: 如果在调用 init() 方法前调用此方法
        """
        self._check_initialized()

        return await self._context.cookies()

    async def save_cookies(self, path: Path | str):
        """
        保存当前浏览器状态（包括 cookies）到指定路径。
        
        Args:
            path (Path | str): 保存状态的文件路径
            
        Raises:
            LoginHelperError: 如果在调用 init() 方法前调用此方法
        """
        self._check_initialized()

        await self._context.storage_state(path=path)

    def _check_initialized(self):
        """
        检查是否已初始化。
        
        检查登录助手是否已通过 init() 方法初始化。
        
        Raises:
            LoginHelperError: 如果登录助手未初始化
        """
        if not self._initialized:
            raise LoginHelperError("call the init() first")


class LoginState(Enum):
    """
    登录状态枚举类。
    
    用于表示用户的登录状态：
    - UNLOGINED: 未登录
    - LOGINED: 已登录
    - AUTHNEEDED: 需要认证
    """
    UNLOGINED = 0
    LOGINED = 1
    AUTHNEEDED = 2
