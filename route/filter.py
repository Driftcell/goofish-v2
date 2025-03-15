import traceback
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import structlog

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


async def global_exception_handler(request: Request, exc: Exception):
    status_code = 500

    if isinstance(exc, HTTPException):
        status_code = exc.status_code

    logger.error(traceback.format_exc())

    return JSONResponse(
        status_code=status_code, content={"code": 1, "message": str(exc)}
    )
