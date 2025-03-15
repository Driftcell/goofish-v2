from typing import List, Union

from pydantic import BaseModel, Field


class Type(BaseModel):
    item_biz_type: int = Field(..., alias="itemBizType")
    goods_type: List[Union[int, str]] = Field(..., alias="goodsType")
    sp_biz_type: str = Field(..., alias="spBizType")
    category_id: int = Field(..., alias="categoryId")
    channel_cat_id: str = Field(..., alias="channelCatId")
    pv_list: List = Field(..., alias="pvList")
    virtual: bool = Field(..., alias="virtual")
    division_id_list: List[str] = Field(..., alias="divisionIdList")
    free_shipping: bool = Field(..., alias="freeShipping")
    reserve_price: float = Field(..., alias="reservePrice")
    quantity: int = Field(..., alias="quantity")
    stuff_status: int = Field(..., alias="stuffStatus")
    transport_fee: int = Field(..., alias="transportFee")
    item_sku_list: List = Field(..., alias="itemSkuList")
    category_name: str = Field(..., alias="categoryName")

    def to_dict(self):
        return self.model_dump(by_alias=True)


class Item(BaseModel):
    title: str
    description: str = Field(..., alias="desc")
    price: float = Field(..., alias="originalPrice")
    outer_id: str = Field(..., alias="outerId")

    def to_dict(self, merge={}):
        return self.model_dump(by_alias=True) | merge
