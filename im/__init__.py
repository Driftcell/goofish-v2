import asyncio
import re

import structlog
from aiohttp import ClientSession
from motor.motor_asyncio import AsyncIOMotorDatabase
from playwright.async_api import Playwright, Route

from helpers.base import LoginHelper

from .types import IMContext, IMTask, IMTaskType

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class GoofishIM(LoginHelper):
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        playwright: Playwright,
        cookies: list,
    ) -> None:
        super().__init__(playwright)
        self._db = db
        self._cookies = cookies
        self._task_queue: asyncio.Queue[IMTask | None] = asyncio.Queue()
        self._initialized_users = False
        self._received: set[tuple[str, int]] = set()

    async def init(self, headless: bool = False, *, cookies=None):
        await super().init(headless, cookies=cookies)

        await self._context.add_cookies(cookies=self._cookies)

        await self._page.route("**/p_im-index.js", handler=self._inject)
        await self._page.expose_function("sendChatMessage", self._on_message)
        await self._page.goto("https://www.goofish.com/im", wait_until="networkidle")

    async def start(self):
        await self._click_all_users()
        self._initialized_users = True
        self._task_executor_task = asyncio.create_task(self._task_executor())
        self._on_received_task = asyncio.create_task(self._on_received())

    async def stop(self):
        await self._task_queue.put(None)
        self._on_received_task.cancel()

    async def send_message(self, userId: str, message: str):
        locator = "#content > div > div > main > div.sendbox--A9eGQCY5 > div.sendbox-bottom--O2c5fyIe > button"
        await self._locate_user(userId)
        await self._page.locator("textarea").fill(message)
        await self._page.locator(locator).click()

    async def send_image(self, userId: str, image: str):
        await self._locate_user(userId)
        await self._page.locator("input[type=file]").set_input_files(image)

    async def _on_received(self):
        while True:
            for session_id, sender_id in self._received:
                next_context = IMContext(session_id=session_id)
                next_task = IMTask(type_=IMTaskType.AIMODEL, context=next_context)

                context = IMContext(sender=sender_id, sleep=30, next_task=next_task)
                task = IMTask(
                    type_=IMTaskType.SLEEP,
                    context=context,
                )

                await self._task_queue.put(task)

            self._received.clear()

            await self._click_all_users()
            await asyncio.sleep(30)

    async def _sleep_task(self, context: IMContext):
        assert context.sleep is not None
        assert context.next_task is not None

        await asyncio.sleep(context.sleep)
        await self._task_queue.put(context.next_task)

    async def _ai_model_task(self, context: IMContext):
        assert context.session_id is not None

        chats = await self._chat_history(context.session_id)

        logger.info(f"chats: {chats}")

    async def _task_executor(self):
        while task := await self._task_queue.get():
            if task is None:
                break

            match task.type_:
                case IMTaskType.SLEEP:
                    logger.info(f"{task.type_}")
                    asyncio.create_task(self._sleep_task(context=task.context))
                case IMTaskType.SENDMSG:
                    logger.info(f"{task.type_}")
                case IMTaskType.SENDIMG:
                    logger.info(f"{task.type_}")
                case IMTaskType.AIMODEL:
                    logger.info(f"{task.type_}")

    async def _chat_history(self, session_id: str):
        chats = (
            await self._db.chats.find({"session_id": session_id})
            .sort("timeStamp", 1)
            .to_list()
        )
        return chats

    async def _users(self):
        locator = (
            "#conv-list-scrollable > div > div.rc-virtual-list-holder > div > div > *"
        )
        return await self._page.query_selector_all(locator)

    async def _click_all_users(self, limits=5):
        users = await self._users()

        for user in users[: min(len(users), limits)]:
            await user.click()
            await self._page.wait_for_load_state("networkidle")
            await self._page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(1)

    async def _locate_user(self, userId: str):
        users = await self._users()

        for user in users:
            await user.click()
            await self._page.wait_for_load_state("networkidle")

            if await self._get_current_userid() == userId:
                return

        raise Exception("Not found the user")

    async def _on_message(self, message):
        try:
            chat = {
                "sessionId": message["message"]["sessionId"],
                "messageId": message["message"]["messageId"],
                "senderId": message["message"]["senderInfo"]["userId"],
                "isMyMsg": message["isMyMsg"],
                "timeStamp": message["message"]["timeStamp"],
                "content": message["message"]["reminder"]["content"],
            }

            if await self._db.chats.find_one(
                {
                    "sessionId": chat["sessionId"],
                    "senderId": chat["senderId"],
                    "messageId": chat["messageId"],
                }
            ):
                return

            if self._initialized_users and not chat["isMyMsg"]:
                self._received.add((chat["sessionId"], chat["senderId"]))

            await self._db.chats.update_one(
                {"sessionId": chat["sessionId"], "messageId": chat["messageId"]},
                {"$set": chat},
                upsert=True,
            )
            logger.info(f"Received new message from {chat['senderId']}")

        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def _inject(self, route: Route):
        url = route.request.url

        async with ClientSession() as session:
            async with session.get(url) as response:
                originalJs = await response.text()

        patchedJs = re.sub(
            r"(C5=function\(ee\){)",
            r"\1window.sendChatMessage(ee);",
            originalJs,
        )

        await route.fulfill(body=patchedJs)

    async def _get_current_userid(self):
        try:
            url = await self._page.locator(
                "#content > div > div > main > div.message-topbar--uzL8Czfo > div.right-container--AxSGn7lz > div:nth-child(1) > a",
            ).get_attribute("href", timeout=2000)

            if url is None:
                return None

            prefix = "https://www.goofish.com/personal?userId="

            return url[len(prefix) :]
        except Exception as e:
            return None
