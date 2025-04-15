from pathlib import Path

import structlog
from playwright.async_api import Playwright

from .base import LoginHelper, LoginState
from .error import LoginHelperError

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class GoofishLoginHelper(LoginHelper):
    """闲鱼登录助手类，用于处理闲鱼网站的登录操作。"""
    
    def __init__(self, playwright: Playwright):
        """
        初始化闲鱼登录助手。
        
        Args:
            playwright: Playwright 实例，用于创建浏览器和页面。
        """
        super().__init__(playwright)

    async def init(self, headless: bool = False, *, cookies = None):
        """
        初始化登录助手，打开闲鱼网站。
        
        Args:
            headless: 是否使用无头模式运行浏览器，默认为 False。
            cookies: 可选的 cookies 数据，用于恢复会话。
            
        Returns:
            None
        """
        await super().init(headless, cookies=cookies)

        # 打开闲鱼首页并等待网络请求完成
        await self._page.goto("https://www.goofish.com/", wait_until="networkidle")

    async def login(self, path: Path | str | None = None):
        """
        执行登录操作，点击登录按钮并保存二维码。
        
        Args:
            path: 保存二维码的路径，可以是 Path 对象或字符串，如果为 None 则不保存到文件。
            
        Returns:
            二维码图像的字节数据。
            
        Raises:
            LoginHelperError: 登录过程中出现错误。
        """
        self._check_initialized()

        await self._click_login_button()
        return await self._save_QRCode(path)

    async def check_login_state(self):
        """
        检查当前的登录状态。
        
        Returns:
            LoginState.UNLOGINED: 如果未登录。
            LoginState.LOGINED: 如果已登录。
        """
        # 检查页面上的昵称元素，如果显示"登录"则表示未登录
        if await self._page.locator("[class^='nick-']").text_content() == "登录":
            return LoginState.UNLOGINED
        else:
            return LoginState.LOGINED

    async def _click_keep_login_button(self):
        """
        点击"保持登录"按钮。
        
        内部方法，用于在登录过程中确认保持登录状态。
        """
        # "保持登录"按钮的 CSS 选择器
        locator = "#login > div.extra-login-content > div > div.login-blocks.block4 > div.keep-login-confirm.show > div > div > div.keep-login-confirm-footer > button.fm-button.fm-submit.keep-login-btn.keep-login-confirm-btn.primary"
        # 获取登录框所在的 iframe
        frame = self._page.frame_locator("#alibaba-login-box")
        await frame.locator(locator).click()

    async def _click_login_button(self):
        """
        点击登录按钮。
        
        内部方法，用于打开登录对话框。
        
        Raises:
            LoginHelperError: 点击登录按钮时出错。
        """
        # 登录按钮的 CSS 选择器
        locator = "#ice-container > div.bottomLead--aH0Oblol > div > div"

        try:
            await self._page.locator(locator).click()
        except Exception as e:
            raise LoginHelperError(f"_click_login_button error: {e}")

        # 等待页面网络请求完成
        await self._page.wait_for_load_state("networkidle")

    async def _save_QRCode(self, path: Path | str | None):
        """
        保存登录二维码。
        
        内部方法，用于获取并可选保存登录二维码。
        
        Args:
            path: 保存二维码的路径，可以是 Path 对象或字符串，如果为 None 则不保存到文件。
            
        Returns:
            二维码图像的字节数据。
            
        Raises:
            LoginHelperError: 保存二维码时出错。
        """
        # 获取登录框所在的 iframe
        frame = self._page.frame_locator("#alibaba-login-box")
        # 定位二维码元素
        qrcode = frame.locator("#login > div.extra-login-content > div")

        try:
            return await qrcode.screenshot(path=path)
        except Exception as e:
            raise LoginHelperError(f"_save_QRCode error: {e}")
