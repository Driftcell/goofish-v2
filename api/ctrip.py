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
    """
    携程API客户端类，用于与携程旅游API进行交互，包括获取产品列表、产品详情、创建短链接等功能。
    同时支持将图片下载并存储到MinIO对象存储中，并将产品信息保存到MongoDB数据库。
    """
    def __init__(
        self,
        cookies: list,
        minio: Minio,
        db: AsyncIOMotorDatabase,
        alliance_id: str,
        sid: str,
    ) -> None:
        """
        初始化携程API客户端
        
        参数:
            cookies: 用于API验证的cookies列表
            minio: MinIO客户端实例，用于存储图片
            db: MongoDB异步数据库实例，用于存储产品信息
            alliance_id: 联盟ID，用于生成带有推广信息的链接
            sid: 站点ID，用于生成带有推广信息的链接
        """
        self._cookies = cookies
        self._minio = minio
        self._db = db
        self._alliance_id = alliance_id
        self._sid = sid

    async def create_short_url(self, session: ClientSession, url: str) -> str:
        """
        创建短链接
        
        参数:
            session: aiohttp客户端会话
            url: 需要转换的长URL
            
        返回:
            str: 生成的短链接URL
        """
        url = os.getenv("CTRIP_CREATE_SHORT_URL_API", "")
        body = {
            "url": f"{url}&allianceid={self._alliance_id}&sid={self._sid}",
            "clientFrom": "PC",
        }

        async with session.post(url, json=body) as response:
            return (await response.json()).get("shortUrl")

    async def find_product_detail(self, session: ClientSession, product_id: str):
        """
        获取产品详细信息
        
        参数:
            session: aiohttp客户端会话
            product_id: 产品ID
            
        返回:
            dict: 包含产品详细信息的字典
        """
        url = os.getenv("CTRIP_PRODUCTION_DETAIL_API", "")
        body = {
            "businessType": "GRP",  # GRP表示跟团游产品类型
            "productId": product_id,
            "sid": self._sid,
            "clientFrom": "PC",
        }

        async with session.post(url, json=body) as response:
            return await response.json()

    async def get_product_list(self, session, page: int, city_name: str) -> list[dict]:
        """
        获取产品列表
        
        参数:
            session: aiohttp客户端会话
            page: 页码，从1开始
            city_name: 城市名称，用于筛选特定城市的产品
            
        返回:
            list[dict]: 产品信息列表
        """
        url = os.getenv("CTRIP_PRODUCTION_API")
        body = {
            "cityName": city_name,
            "pageIndex": page,
            "pageSize": 10,  # 每页10条记录
            "subTabType": "",
            "subTabValue": "",
            "tabValue": "hotPush",  # 热门推荐类型
            "clientFrom": "PC",
        }

        async with session.post(url, json=body) as response:
            return (await response.json()).get("productInfoList", [])

    async def _download_image(
        self, session: ClientSession, img_url: str, *, bucket_name="images"
    ):
        """
        下载单张图片并保存到MinIO中
        
        参数:
            session: aiohttp客户端会话
            img_url: 图片URL
            bucket_name: MinIO中的桶名称，默认为"images"
        """
        img_name = img_url.split("/")[-1]  # 从URL中提取图片名称
        try:
            # 检查图片是否已存在于MinIO中
            await asyncio.to_thread(self._minio.stat_object, bucket_name, img_name)
        except S3Error as e:
            if e.code == "NoSuchKey":  # 图片不存在，需要下载
                async with session.get(img_url) as response:
                    data = await response.read()

                    # 将图片上传到MinIO
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
        """
        从队列中获取图片URL并下载，作为消费者任务运行
        
        参数:
            q: 包含图片URL的异步队列
            bucket_name: MinIO中的桶名称，默认为"images"
        """
        async with ClientSession() as session:
            while True:
                img_url = await q.get()

                if img_url is None:  # None作为结束信号
                    q.task_done()
                    break

                try:
                    await self._download_image(
                        session, img_url, bucket_name=bucket_name
                    )
                except Exception as e:
                    logger.error(f"Failed when download {img_url}, skip it: {e}")
                finally:
                    q.task_done()  # 通知队列任务已完成

    async def run(
        self, city_name: str, *, download_images_task_num=10, bucket_name="images"
    ):
        """
        运行主流程，获取产品列表和详情，下载图片并存储数据
        
        参数:
            city_name: 城市名称
            download_images_task_num: 图片下载任务的并发数，默认为10
            bucket_name: MinIO中的桶名称，默认为"images"
        """
        # 创建图片下载队列
        images_queue = asyncio.Queue()
        # 创建多个图片下载任务
        download_images_tasks = [
            asyncio.create_task(
                self._download_images(images_queue, bucket_name=bucket_name)
            )
            for _ in range(download_images_task_num)
        ]
        page = 1
        async with ClientSession(cookies=self._cookies) as session:
            # 循环获取所有页的产品列表，当没有更多产品时退出
            while products := await self.get_product_list(session, page, city_name):
                logger.info(f"Collecting page {page}")
                page += 1

                # 为每个产品创建获取详情的任务
                find_details_tasks = [
                    self.find_product_detail(session, product["productId"])
                    for product in products
                ]

                # 并发获取所有产品详情
                responses = await asyncio.gather(
                    *find_details_tasks, return_exceptions=True
                )

                store_details_tasks = []

                # 处理每个产品的详情
                for response in responses:
                    if isinstance(response, BaseException):
                        logger.warn("Exception, skip.")
                        continue

                    if "productDetail" not in response:
                        logger.info("Not found the product details, skip.")
                        continue

                    response = response["productDetail"]
                    # 将产品的所有图片URL加入下载队列
                    for img_url in response["imgList"]:
                        await images_queue.put(img_url)

                    # 创建短链接
                    response["shortUrl"] = await self.create_short_url(
                        session, response["skipUrl"]
                    )

                    # 创建数据库更新任务
                    task = self._db.goods.update_one(
                        {
                            "productId": response["productId"],
                        },
                        {"$set": response},
                        upsert=True,  # 不存在则插入
                    )
                    store_details_tasks.append(task)

                # 并发执行所有数据库更新任务
                await asyncio.gather(*store_details_tasks, return_exceptions=True)

        logger.info("Waiting for download images tasks to complete...")

        # 向每个图片下载任务发送结束信号
        for _ in range(download_images_task_num):
            await images_queue.put(None)

        # 等待所有图片下载完成
        await images_queue.join()
        await asyncio.gather(*download_images_tasks)

        logger.info("All tasks completed.")
