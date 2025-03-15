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
