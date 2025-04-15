import asyncio
from hashlib import md5
from io import BytesIO

from fastapi import APIRouter, Depends, File, UploadFile
from minio import Minio

from .depends import get_minio
from .types import MyResponse, Upload

router = APIRouter(tags=["upload"])


@router.post("/upload", response_model=MyResponse[Upload])
async def p_upload(file: UploadFile = File(...), minio: Minio = Depends(get_minio)):
    """
    处理文件上传
    
    接收上传的文件，计算MD5哈希值作为文件名的一部分，并将文件保存到MinIO对象存储中。
    
    Args:
        file (UploadFile): 通过表单上传的文件
        minio (Minio): MinIO客户端连接，通过依赖注入获取
        
    Returns:
        MyResponse[Upload]: 包含上传成功信息的响应，包括存储桶名称和对象名称
        
    Raises:
        AssertionError: 当文件名为None时抛出
    """
    file_bytes = await file.read()
    assert file.filename is not None
    postfix = file.filename.rsplit(".")[0]
    result = await asyncio.to_thread(
        minio.put_object,
        bucket_name="upload",
        object_name=f"{md5(file_bytes).hexdigest}.{postfix}",
        data=BytesIO(file_bytes),
        length=len(file_bytes),
        content_type="image/png" if postfix == "png" else "image/jpeg",
    )

    return MyResponse(
        data=Upload(bucket_name=result.bucket_name, object_name=result.object_name)
    )
