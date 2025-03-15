import os
from hashlib import md5
from pathlib import Path
from typing import Literal

import aiofiles
import aiohttp
import structlog
from minio import Minio, S3Error

from .error import ApiError

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class AgisoApi:
    def __init__(self, cookies: list, token: str, minio: Minio) -> None:
        self._cookies = cookies
        self._token = token
        self._headers = {"Authorization": f"Bearer {self._token}"}
        self._minio = minio

    async def search_good_list(self):
        url = os.getenv("AGISO_SEARCH_GOODS_LIST_API", "")
        body = {"pageSize": 100, "page": 1, "status": "0", "categoryId": ""}
        goods = []

        async with aiohttp.ClientSession(
            cookies=self._cookies, headers=self._headers
        ) as session:
            while True:
                async with session.post(url, json=body) as response:
                    if response.status != 200:
                        raise ApiError(f"Response with status code {response.status}")

                    data = await response.json()
                    for good in data["data"]["data"]["items"]:
                        goods.append(good)

                if data["data"]["data"]["hasNextPages"]:
                    body["page"] += 1
                else:
                    break

        return goods

    async def update_item_status(self, id: str, online: bool):
        url = os.getenv("AGISO_UPDATE_ITEM_STATUS_API", "")
        body = {"online": online, "goodsId": id}

        async with aiohttp.ClientSession(
            cookies=self._cookies, headers=self._headers
        ) as session:
            async with session.post(url, json=body) as response:
                if response.status != 200:
                    raise ApiError(f"Response with status code {response.status}")

                data = await response.json()
                if not data.get("data", {}).get("isSuccess", False):
                    raise ApiError(f"Failed to update item status")

    async def upload_images(self, image: Path | str | bytes):
        if isinstance(image, (Path, str)):
            if not os.path.exists(image):
                raise FileExistsError(f"{image} does not exists")

            async with aiofiles.open(image, "br") as f:
                image = await f.read()

        url = os.getenv("AGISO_UPLOAD_IMAGE_API", "")
        form = aiohttp.FormData()
        form.add_field(
            "files",
            image,
            filename=f"{md5(image).hexdigest()}.png",
            content_type="image/png",
        )

        async with aiohttp.ClientSession(
            cookies=self._cookies, headers=self._headers
        ) as session:
            async with session.post(url, data=form) as response:
                if response.status != 200:
                    raise ApiError(f"Response code: {response.status}")

                data = await response.json()
                statusCode = data.get("statusCode")
                if statusCode != 200:
                    raise ApiError(f"Response code: {statusCode}")

                return data["data"]["data"]

    async def upload_item(
        self,
        item,
        *,
        draft=False,
        price_mode=Literal["fixed", "smart"],
        price=0.01,
        template: str | None = None,
    ):
        imgs = []
        for image in item["imgList"]:
            try:
                obj = self._minio.stat_object(bucket_name="images", object_name=image)
                assert obj.size is not None

                if obj.size >= 10 * 1024 * 1024:
                    logger.warn(
                        "Image size is larger than 10MB", image=image, size=obj.size
                    )
                    continue

                obj = self._minio.get_object(bucket_name="images", object_name=image)
                image_bytes = obj.read()

                imgs.append(await self.upload_images(image_bytes))
            except S3Error as e:
                if e.code == "NoSuchKey":
                    logger.warn("No such image", image=image)
            except Exception as e:
                logger.error("Upload image error", error=e)

        if not imgs:
            logger.warn("Failed to upload any images, skip.")
            return

        if template:
            logger.info("Formatting template with item information", item_id=item.get("productId", "unknown"))
            goods_content_without_link = [
            f"{short_url['description']}" for short_url in item["shortUrls"]
            ]
            try:
                template = template.format(
                    goods_information=item.get("copywriterInfo", ""),
                    goods_content_without_link="\n".join(goods_content_without_link),
                )
                logger.debug("Template successfully formatted")
            except Exception as e:
                logger.error("Failed to format template", error=str(e), item_id=item.get("productId", "unknown"))
                template = item.get("copywriterInfo", "")
        else:
            logger.info("Using default template from item copywriterInfo")
            template = item.get("copywriterInfo", "")

        body = {
            "itemBizType": 2,
            "goodsType": [
                25,
                "ed8a1d72cd74ed15bff01601e0dc334b",
                "021d57d22fe2f314752d0938bcc4ba3b",
                "c65beb619804c0b828d88a08a19453dc",
            ],
            "spBizType": "25",
            "categoryId": 50025461,
            "channelCatId": "c65beb619804c0b828d88a08a19453dc",
            "pvList": [],
            "virtual": True,
            "title": item.get("title") or item.get("subName"),
            "desc": template,
            "divisionIdList": ["110000", "110100", "110101"],
            "freeShipping": True,
            "reservePrice": price if price_mode == "fixed" else item["price"],
            "originalPrice": item.get("price") or 0.01,
            "quantity": 1,
            "outerId": item.get("productId"),
            "stuffStatus": 0,
            "transportFee": 0,
            "itemSkuList": [],
            "imgList": imgs,
            "categoryName": "卡券/票务/旅游出行/旅游出行/其他酒店优惠券",
        }

        async with aiohttp.ClientSession(
            cookies=self._cookies, headers=self._headers
        ) as session:
            async with session.post(
                (
                    os.getenv("AGISO_INSERT_DRAFT_API", "")
                    if draft
                    else os.getenv("AGISO_PUBLISH_API", "")
                ),
                json=body,
            ) as response:
                if response.status != 200:
                    raise ApiError(
                        f"Failed to insert draft, status code: {response.status}"
                    )

                data = await response.json()
                status_code = data.get("statusCode")
                if status_code != 200 or data.get("succeeded") != True:
                    raise ApiError(
                        f"Failed to insert draft, status code: {status_code}"
                    )
