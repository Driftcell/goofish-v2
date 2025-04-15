import asyncio

import structlog
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from structlog.dev import ConsoleRenderer

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)
console_renderer = ConsoleRenderer()
connected_clients = set()

router = APIRouter(tags=["log"])


def sse_processor(logger, method_name, event_dict):
    """
    日志事件处理器
    
    将结构化日志事件转换为SSE格式并推送给所有已连接的客户端。
    
    Args:
        logger: 日志记录器对象
        method_name (str): 日志方法名称
        event_dict (dict): 日志事件字典
        
    Returns:
        dict: 原始日志事件字典，用于继续传递给其他处理器
    """
    if connected_clients:
        colored_log = console_renderer(None, method_name, event_dict)
        message = f"data: {colored_log}\n\n"
        asyncio.create_task(push_log_to_clients(message))

    return event_dict


async def push_log_to_clients(message):
    """
    将日志消息推送给所有已连接的客户端
    
    遍历所有已连接的客户端队列，将日志消息推送到队列中。
    
    Args:
        message (str): 要推送的日志消息，格式为SSE兼容格式
    """
    for queue in list(connected_clients):
        assert isinstance(queue, asyncio.Queue)
        try:
            await queue.put(message)
        except asyncio.QueueFull:
            pass


async def event_stream():
    """
    SSE事件流生成器
    
    为每个连接的客户端创建一个事件流，从队列中获取日志消息并发送给客户端。
    
    Yields:
        str: SSE格式的日志消息
    """
    queue = asyncio.Queue(maxsize=10)
    connected_clients.add(queue)
    try:
        while True:
            data = await queue.get()
            yield data
    except asyncio.CancelledError:
        pass
    finally:
        connected_clients.discard(queue)


@router.get("/logs")
async def get_logs():
    """
    获取实时日志流
    
    提供SSE端点，允许客户端通过HTTP连接实时接收服务器日志。
    
    Returns:
        StreamingResponse: 包含日志事件流的流式响应对象
    """
    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/logs/test")
async def test_logs():
    """
    测试日志功能
    
    生成测试日志消息，用于验证日志系统是否正常工作。
    
    Returns:
        None: 此函数通过副作用（生成日志）工作，不返回响应数据
    """
    logger.info("test!")


@router.get("/error")
async def error():
    """
    触发测试异常
    
    引发一个测试异常，用于测试全局异常处理器的功能。
    
    Raises:
        Exception: 始终抛出一个测试异常
    """
    raise Exception("This is a test exception")
