from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")

class ErrorResponse(BaseModel):
    """
    错误响应模型
    
    定义API错误响应的标准格式。
    
    Attributes:
        code (int): 错误码，默认为1表示错误
        message (str): 错误信息描述
        data (Optional[Any]): 可选的附加数据，默认为None
    """
    code: int = 1
    message: str = "error"
    data: Optional[Any] = None

class MyResponse(BaseModel, Generic[T]):
    """
    通用响应模型
    
    定义API成功响应的标准格式，支持泛型数据类型。
    
    Attributes:
        code (int): 状态码，默认为0表示成功
        message (str): 状态信息描述
        data (T): 响应数据，类型由泛型参数T决定
    """
    code: int = 0
    message: str = "ok"
    data: T


class Config(BaseModel):
    """
    配置模型
    
    用于存储和传输键值对形式的配置项。
    
    Attributes:
        name (Optional[str]): 配置项名称
        value (Optional[Any]): 配置项的值
    """
    name: Optional[str] = None
    value: Optional[Any] = None

class Price(BaseModel):
    """
    价格模型
    
    定义价格的模式和具体数值。
    
    Attributes:
        mode (str): 价格模式，默认为"fixed"（固定价格）
        value (Optional[str]): 价格值，默认为"0.01"
    """
    mode: str = "fixed"
    value: Optional[str] = "0.01"


class ConfigT(BaseModel):
    """
    类型化配置模型
    
    包含应用程序运行所需的各项具体配置参数。
    
    Attributes:
        time_delta (str): 任务执行时间间隔（秒），默认为"60"
        item_limits (str): 商品数量限制，默认为"3000"
        price (Price): 价格配置对象，默认使用Price默认值
        item_type (str): 商品类型，默认为"家居/服务/跑腿代办/酒店代订"
    """
    time_delta: str = "60"
    item_limits: str = "3000"
    price: Price = Price()
    item_type: str = "家居/服务/跑腿代办/酒店代订"

class Upload(BaseModel):
    """
    上传文件信息模型
    
    存储上传到对象存储的文件信息。
    
    Attributes:
        bucket_name (str): 存储桶名称
        object_name (str): 对象名称（文件名）
    """
    bucket_name: str
    object_name: str

class ShortUrl(BaseModel):
    """
    短链接模型
    
    存储商品相关的短链接信息。
    
    Attributes:
        shortUrl (str): 短链接URL
        description (str): 短链接描述
    """
    shortUrl: str
    description: str


class Item(BaseModel):
    """
    商品模型
    
    存储和表示商品的完整信息。
    
    Attributes:
        productId (str): 商品ID
        copywriterInfo (str): 商品文案信息
        endSaleTimeDesc (str): 结束销售时间描述
        imgList (list[str]): 商品图片URL列表
        originalProductId (list[str]): 原始商品ID列表
        price (int): 商品价格
        shortUrls (list[ShortUrl]): 相关短链接列表
        subName (str): 商品副名称
        title (str): 商品标题
    """
    productId: str
    copywriterInfo: str
    endSaleTimeDesc: str
    imgList: list[str]
    originalProductId: list[str]
    price: int
    shortUrls: list[ShortUrl]
    subName: str
    title: str