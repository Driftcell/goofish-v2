import structlog
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class MongoDB:
    _instance = None

    def __new__(cls, *args, **kwargs):
        # 此方法用于实现单例模式，确保只创建一个MongoDB实例
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, uri: str, db_name: str):
        # 初始化MongoDB，建立数据库连接
        if not hasattr(self, "_initialized"):
            logger.info("Initializing MongoDB")
            # 创建MongoDB异步客户端并连接到指定的数据库
            self.client = AsyncIOMotorClient(uri)
            self.db = self.client[db_name]
            self._initialized = True

    @staticmethod
    def get_db() -> "AsyncIOMotorDatabase":
        # 获取MongoDB数据库实例，如果未初始化则抛出异常
        if not MongoDB._instance:
            logger.error("MongoDB is not initialized")
            # 抛出错误，提示用户先进行初始化：MongoDB(uri, db_name)
            raise RuntimeError(
                "MongoDB is not initialized. Call MongoDB(uri, db_name) first."
            )
        return MongoDB._instance.db
