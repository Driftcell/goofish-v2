from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from .depends import get_db
from .types import Item

router = APIRouter(tags=["item"])


@router.get("/items", response_model=list[Item])
async def g_items(
    page: int, page_size: int, db: AsyncIOMotorDatabase = Depends(get_db)
):
    items = (
        await db.items.find().skip((page - 1) * page_size).limit(page_size).to_list()
    )
    items = [Item.model_validate(item) for item in items]

    return items
