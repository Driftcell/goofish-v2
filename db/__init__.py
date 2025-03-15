import structlog
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class MongoDB:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, uri: str, db_name: str):
        if not hasattr(self, "_initialized"):
            logger.info("Initializing MongoDB")
            self.client = AsyncIOMotorClient(uri)
            self.db = self.client[db_name]
            self._initialized = True

    @staticmethod
    def get_db() -> "AsyncIOMotorDatabase":
        if not MongoDB._instance:
            logger.error("MongoDB is not initialized")
            raise RuntimeError(
                "MongoDB is not initialized. Call MongoDB(uri, db_name) first."
            )
        return MongoDB._instance.db
