from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class MyResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "ok"
    data: T


class Config(BaseModel):
    name: Optional[str] = None
    value: Optional[Any] = None

class Price(BaseModel):
    mode: str = "fixed"
    value: Optional[str] = None


class ConfigT(BaseModel):
    time_delta: str = ""
    item_limits: str = ""
    price: Price = Price()
    item_type: str = ""

class Upload(BaseModel):
    bucket_name: str
    object_name: str

class ShortUrl(BaseModel):
    shortUrl: str
    description: str


class Item(BaseModel):
    productId: str
    copywriterInfo: str
    endSaleTimeDesc: str
    imgList: list[str]
    originalProductId: list[str]
    price: int
    shortUrls: list[ShortUrl]
    subName: str
    title: str