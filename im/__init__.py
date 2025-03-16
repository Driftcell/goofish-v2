import asyncio
import re
from urllib.parse import parse_qs, urlparse

import structlog
from aiohttp import ClientSession
from motor.motor_asyncio import AsyncIOMotorDatabase
from playwright.async_api import Playwright, Route

from helpers.base import LoginHelper, LoginState
from route.utils import build_config

from .types import IMContext, IMTask, IMTaskType

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class GoofishIM(LoginHelper):
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        playwright: Playwright,
        cookies: list,
        *,
        token: str | None = None,
    ) -> None:
        super().__init__(playwright)
        self._db = db
        self._cookies = cookies
        self._task_queue: asyncio.Queue[IMTask | None] = asyncio.Queue()
        self._initialized_users = False
        self._received: set[tuple[str, int]] = set()
        self._token = token
        logger.info("GoofishIM instance created", token_provided=token is not None)

    async def init(self, headless: bool = False, *, cookies=None):
        logger.info("Initializing GoofishIM", headless=headless)
        await super().init(headless, cookies=cookies)

        await self._context.add_cookies(cookies=self._cookies)
        logger.debug("Cookies added to browser context")

        await self._page.route("**/p_im-index.js", handler=self._inject)
        logger.info("JavaScript injection route handler set up")

        await self._page.expose_function("sendChatMessage", self._on_message)
        logger.info("Exposed sendChatMessage function to browser")

        logger.info("Navigating to Goofish IM page")
        await self._page.goto("https://www.goofish.com/im", wait_until="networkidle")
        logger.info("Navigation to Goofish IM complete")

    async def start(self):
        logger.info("Starting GoofishIM service")
        await self._click_all_users()
        self._initialized_users = True
        self._task_executor_task = asyncio.create_task(self._task_executor())
        self._on_received_task = asyncio.create_task(self._on_received())
        self._check_login_state_task = asyncio.create_task(self._check_login_state())
        logger.info(
            "GoofishIM service started successfully",
            task_executor_running=True,
            received_task_running=True,
        )

    async def stop(self):
        logger.info("Stopping GoofishIM service")
        await self._task_queue.put(None)
        self._on_received_task.cancel()
        await self._playwright.stop()
        logger.info("GoofishIM service stopping tasks completed")

    async def send_message(self, userId: str, message: str):
        logger.info("Sending message", user_id=userId, message_length=len(message))
        locator = "#content > div > div > main > div.sendbox--A9eGQCY5 > div.sendbox-bottom--O2c5fyIe > button"
        await self._locate_user(userId)
        await self._page.locator("textarea").fill(message)
        await self._page.locator(locator).click()
        logger.info("Message sent successfully", user_id=userId)

    async def send_image(self, userId: str, image: str):
        logger.info("Sending image", user_id=userId, image_path=image)
        await self._locate_user(userId)
        await self._page.locator("input[type=file]").set_input_files(image)
        logger.info("Image sent successfully", user_id=userId, image_path=image)

    async def _on_received(self):
        logger.info("Starting message reception monitoring loop")
        while True:
            logger.debug(f"Processing {len(self._received)} received messages")
            for session_id, sender_id in self._received:
                next_context = IMContext(sender=sender_id, session_id=session_id)
                next_task = IMTask(type_=IMTaskType.AIMODEL, context=next_context)

                context = IMContext(sender=sender_id, sleep=10, next_task=next_task)
                task = IMTask(
                    type_=IMTaskType.SLEEP,
                    context=context,
                )

                logger.debug(
                    "Queueing sleep and AI model task",
                    session_id=session_id,
                    sender_id=sender_id,
                )
                await self._task_queue.put(task)

            self._received.clear()

            logger.debug("Checking all users for new messages")
            await self._click_all_users()
            logger.debug("Sleeping for 30 seconds before next check")
            await asyncio.sleep(30)

    async def _sleep_task(self, context: IMContext):
        assert context.sleep is not None
        assert context.next_task is not None

        logger.debug("Starting sleep task", sleep_duration=context.sleep)
        await asyncio.sleep(context.sleep)
        logger.debug(
            "Sleep task completed, queueing next task",
            next_task_type=context.next_task.type_,
        )
        await self._task_queue.put(context.next_task)

    async def _ai_model_task(self, context: IMContext):
        assert context.session_id is not None

        logger.info("Processing AI model task", session_id=context.session_id)

        chats = await self._chat_history(context.session_id)
        logger.info(
            "Retrieved chat history",
            session_id=context.session_id,
            chat_count=len(chats),
        )

        item_id = await self._get_current_item_id()
        format_set = {
            "information": "",
            "information_without_url": "",
        }
        if item_id and (item := await self._db.items.find_one({"productId": item_id})):
            logger.info(
                "Found target item", item_id=item_id, item_found=item is not None
            )
            format_set["information"] = "\n".join(
                [
                    f"{short_url['description']}\n{short_url['shortUrl']}"
                    for short_url in item["shortUrls"]
                ]
            )
            format_set["information_without_url"] = "\n".join(
                [f"{short_url['description']}" for short_url in item["shortUrls"]]
            )

        if self._token:
            logger.info("Attempting to build config with token")
            if config := await build_config(self._token, self._db):
                if reply := config["reply"]["template"]:
                    assert isinstance(reply, str)
                    reply = reply.format(
                        information=format_set["information"],
                        information_without_url=format_set["information_without_url"],
                    )
                    logger.info("Sending reply using template", reply=reply)
                    await self.send_message(str(context.sender), reply)
        else:
            logger.warning("No token available, skipping reply template")

    async def _task_executor(self):
        logger.info("Task executor started")
        while True:
            task = await self._task_queue.get()
            if task is None:
                logger.info("Received termination signal, shutting down task executor")
                break

            logger.debug("Processing task", task_type=task.type_)

            match task.type_:
                case IMTaskType.SLEEP:
                    logger.info(
                        "Executing sleep task",
                        task_type=task.type_,
                        context=task.context,
                    )
                    asyncio.create_task(self._sleep_task(context=task.context))
                case IMTaskType.SENDMSG:
                    logger.info(
                        "Executing send message task",
                        task_type=task.type_,
                        context=task.context,
                    )
                case IMTaskType.SENDIMG:
                    logger.info(
                        "Executing send image task",
                        task_type=task.type_,
                        context=task.context,
                    )
                case IMTaskType.AIMODEL:
                    logger.info(
                        "Executing AI model task",
                        task_type=task.type_,
                        context=task.context,
                    )
                    asyncio.create_task(self._ai_model_task(context=task.context))

    async def _chat_history(self, session_id: str):
        logger.debug("Fetching chat history", session_id=session_id)
        chats = (
            await self._db.chats.find({"session_id": session_id})
            .sort("timeStamp", 1)
            .to_list()
        )
        logger.debug(
            "Chat history retrieved", session_id=session_id, message_count=len(chats)
        )
        return chats

    async def _users(self):
        logger.debug("Getting user list")
        locator = (
            "#conv-list-scrollable > div > div.rc-virtual-list-holder > div > div > *"
        )
        users = await self._page.query_selector_all(locator)
        logger.debug("User list retrieved", user_count=len(users))
        return users

    async def _click_all_users(self, limits=5):
        logger.info("Clicking all users", limit=limits)
        users = await self._users()
        user_count = min(len(users), limits)

        logger.debug(f"Will click {user_count} users")
        for i, user in enumerate(users[:user_count]):
            logger.debug(f"Clicking user {i+1}/{user_count}")
            await user.click()
            await self._page.wait_for_load_state("networkidle")
            await self._page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(1)
        logger.info("Finished clicking all users", clicked_count=user_count)

    async def _locate_user(self, userId: str):
        logger.info("Locating user", user_id=userId)
        users = await self._users()

        for i, user in enumerate(users):
            logger.debug(f"Checking user {i+1}/{len(users)}")
            await user.click()
            await self._page.wait_for_load_state("networkidle")

            current_id = await self._get_current_userid()
            if current_id == userId:
                logger.info("User found", user_id=userId, position=i + 1)
                return

        logger.error("User not found", user_id=userId)
        raise Exception(f"User {userId} not found")

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

            logger.debug(
                "Message received",
                session_id=chat["sessionId"],
                sender_id=chat["senderId"],
                is_my_message=chat["isMyMsg"],
            )

            existing_message = await self._db.chats.find_one(
                {
                    "sessionId": chat["sessionId"],
                    "senderId": chat["senderId"],
                    "messageId": chat["messageId"],
                }
            )

            if existing_message:
                # logger.debug("Message already exists in database, skipping", message_id=chat["messageId"])
                return

            if self._initialized_users and not chat["isMyMsg"]:
                self._received.add((chat["sessionId"], chat["senderId"]))
                logger.info(
                    "Added message to received queue",
                    session_id=chat["sessionId"],
                    sender_id=chat["senderId"],
                )

            await self._db.chats.update_one(
                {"sessionId": chat["sessionId"], "messageId": chat["messageId"]},
                {"$set": chat},
                upsert=True,
            )
            # logger.info("Saved new message to database",
            #            session_id=chat["sessionId"],
            #            sender_id=chat["senderId"],
            #            message_id=chat["messageId"],
            #            content_length=len(chat["content"]))

        except Exception as e:
            logger.error("Error handling message", error=str(e), exc_info=True)

    async def _inject(self, route: Route):
        logger.debug("Injecting JS", url=route.request.url)
        url = route.request.url

        try:
            async with ClientSession() as session:
                async with session.get(url) as response:
                    originalJs = await response.text()
                    logger.debug("Original JS fetched", content_length=len(originalJs))

            patchedJs = re.sub(
                r"(C5=function\(ee\){)",
                r"\1window.sendChatMessage(ee);",
                originalJs,
            )
            logger.debug("JS successfully patched")

            await route.fulfill(body=patchedJs)
            logger.info("Injected modified JS successfully")
        except Exception as e:
            logger.error("Failed to inject JS", error=str(e), exc_info=True)
            # Fall back to original behavior
            await route.continue_()

    async def _get_current_userid(self):
        try:
            logger.debug("Getting current user ID")
            url = await self._page.locator(
                "#content > div > div > main > div.message-topbar--uzL8Czfo > div.right-container--AxSGn7lz > div:nth-child(1) > a",
            ).get_attribute("href", timeout=2000)

            if url is None:
                logger.debug("No user ID found (no URL)")
                return None

            prefix = "https://www.goofish.com/personal?userId="
            user_id = url[len(prefix) :]
            logger.debug("Current user ID", user_id=user_id)
            return user_id
        except Exception as e:
            logger.warning("Failed to get current user ID", error=str(e))
            return None

    async def _get_current_item_id(self):
        try:
            logger.debug("Getting current item ID")
            url = await self._page.locator(
                "#content > div > div > main > div:nth-child(2) > div > div.left--UqpSF6uz > a",
            ).get_attribute("href", timeout=2000)

            if url is None:
                logger.debug("No item ID found (no URL)")
                return None

            qs = parse_qs(urlparse(url, allow_fragments=False).query)
            item_id = qs.get("id", [None])[0]
            logger.debug("Current item ID", item_id=item_id)
            return item_id
        except Exception as e:
            logger.warning("Failed to get current item ID", error=str(e))
            return None

    async def _login_state(self):
        if await self._page.locator("[class^='nick-']").text_content() == "登录":
            return LoginState.UNLOGINED
        else:
            return LoginState.LOGINED

    async def _check_login_state(self):
        logger.info("Checking login state")
        while True:
            state = await self._login_state()
            if state == LoginState.UNLOGINED:
                logger.warning("User is not logged in")

                await self._db.users.update_one(
                    {"token": self._token}, {"$set": {"expired": True}}
                )

                break
            await asyncio.sleep(10)
