from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from .depends import get_db
from .types import Item

router = APIRouter(tags=["item"])


@router.get("/items", response_model=list[Item])
async def g_items(
    page: int, page_size: int, db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    获取分页的商品列表
    
    根据页码和每页数量参数，从数据库中分页获取商品数据。
    
    Args:
        page (int): 当前页码，从1开始
        page_size (int): 每页显示的商品数量
        db (AsyncIOMotorDatabase): 数据库连接，通过依赖注入获取
        
    Returns:
        list[Item]: 商品对象列表
    """
    items = (
        await db.items.find().skip((page - 1) * page_size).limit(page_size).to_list()
    )
    items = [Item.model_validate(item) for item in items]

    return items
