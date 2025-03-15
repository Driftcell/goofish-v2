import asyncio
import errno
import os
from io import BytesIO

import aiofiles
import structlog
from aiohttp import ClientSession
from minio import Minio, S3Error
from motor.motor_asyncio import AsyncIOMotorDatabase

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class CtripApi:
    def __init__(
        self,
        cookies: list,
        minio: Minio,
        db: AsyncIOMotorDatabase,
        alliance_id: str,
        sid: str,
    ) -> None:
        self._cookies = cookies
        self._minio = minio
        self._db = db
        self._alliance_id = alliance_id
        self._sid = sid

    async def create_short_url(self, session: ClientSession, url: str) -> str:
        url = os.getenv("CTRIP_CREATE_SHORT_URL_API", "")
        body = {
            "url": f"{url}&allianceid={self._alliance_id}&sid={self._sid}",
            "clientFrom": "PC",
        }

        async with session.post(url, json=body) as response:
            return (await response.json()).get("shortUrl")

    async def find_product_detail(self, session: ClientSession, product_id: str):
        url = os.getenv("CTRIP_PRODUCTION_DETAIL_API", "")
        body = {
            "businessType": "GRP",
            "productId": product_id,
            "sid": self._sid,
            "clientFrom": "PC",
        }

        async with session.post(url, json=body) as response:
            return await response.json()

    async def get_product_list(self, session, page: int, city_name: str) -> list[dict]:
        url = os.getenv("CTRIP_PRODUCTION_API")
        body = {
            "cityName": city_name,
            "pageIndex": page,
            "pageSize": 10,
            "subTabType": "",
            "subTabValue": "",
            "tabValue": "hotPush",
            "clientFrom": "PC",
        }

        async with session.post(url, json=body) as response:
            return (await response.json()).get("productInfoList", [])

    async def _download_image(
        self, session: ClientSession, img_url: str, *, bucket_name="images"
    ):
        img_name = img_url.split("/")[-1]
        try:
            await asyncio.to_thread(self._minio.stat_object, bucket_name, img_name)
        except S3Error as e:
            if e.code == "NoSuchKey":
                async with session.get(img_url) as response:
                    data = await response.read()

                    await asyncio.to_thread(
                        self._minio.put_object,
                        bucket_name,
                        img_name,
                        BytesIO(data),
                        len(data),
                        content_type="image/jpeg",
                    )
            else:
                logger.error(f"S3Error: {e}")

    async def _download_images(self, q: asyncio.Queue, *, bucket_name="images"):
        async with ClientSession() as session:
            while True:
                img_url = await q.get()

                if img_url is None:
                    q.task_done()
                    break

                try:
                    await self._download_image(
                        session, img_url, bucket_name=bucket_name
                    )
                except Exception as e:
                    logger.error(f"Failed when download {img_url}, skip it: {e}")
                finally:
                    q.task_done()

    async def run(
        self, city_name: str, *, download_images_task_num=10, bucket_name="images"
    ):
        images_queue = asyncio.Queue()
        download_images_tasks = [
            asyncio.create_task(
                self._download_images(images_queue, bucket_name=bucket_name)
            )
            for _ in range(download_images_task_num)
        ]
        page = 1
        async with ClientSession(cookies=self._cookies) as session:
            while products := await self.get_product_list(session, page, city_name):
                logger.info(f"Collecting page {page}")
                page += 1

                find_details_tasks = [
                    self.find_product_detail(session, product["productId"])
                    for product in products
                ]

                responses = await asyncio.gather(
                    *find_details_tasks, return_exceptions=True
                )

                store_details_tasks = []

                for response in responses:
                    if isinstance(response, BaseException):
                        logger.warn("Exception, skip.")
                        continue

                    if "productDetail" not in response:
                        logger.info("Not found the product details, skip.")
                        continue

                    response = response["productDetail"]
                    for img_url in response["imgList"]:
                        await images_queue.put(img_url)

                    response["shortUrl"] = await self.create_short_url(
                        session, response["skipUrl"]
                    )

                    task = self._db.goods.update_one(
                        {
                            "productId": response["productId"],
                        },
                        {"$set": response},
                        upsert=True,
                    )
                    store_details_tasks.append(task)

                await asyncio.gather(*store_details_tasks, return_exceptions=True)

        logger.info("Waiting for download images tasks to complete...")

        for _ in range(download_images_task_num):
            await images_queue.put(None)

        await images_queue.join()
        await asyncio.gather(*download_images_tasks)

        logger.info("All tasks completed.")
