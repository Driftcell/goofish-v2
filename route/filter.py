import traceback
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import structlog

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


async def global_exception_handler(request: Request, exc: Exception):
    """
    全局异常处理器
    
    捕获并处理应用程序中的所有未捕获异常，将其转换为标准化的JSON响应。
    
    Args:
        request (Request): 当前处理的HTTP请求对象
        exc (Exception): 捕获到的异常对象
        
    Returns:
        JSONResponse: 包含错误信息的标准化JSON响应
        
    Notes:
        - 如果异常是HTTPException类型，使用其状态码
        - 其他类型异常默认返回500状态码
        - 记录完整的异常追踪信息到日志
    """
    status_code = 500

    if isinstance(exc, HTTPException):
        status_code = exc.status_code

    logger.error(traceback.format_exc())

    return JSONResponse(
        status_code=status_code, content={"code": 1, "message": str(exc)}
    )
