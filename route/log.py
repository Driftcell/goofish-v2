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
    if connected_clients:
        colored_log = console_renderer(None, method_name, event_dict)
        message = f"data: {colored_log}\n\n"
        asyncio.create_task(push_log_to_clients(message))

    return event_dict


async def push_log_to_clients(message):
    for queue in list(connected_clients):
        assert isinstance(queue, asyncio.Queue)
        try:
            await queue.put(message)
        except asyncio.QueueFull:
            pass


async def event_stream():
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
    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/logs/test")
async def test_logs():
    logger.info("test!")


@router.get("/error")
async def error():
    raise Exception("This is a test exception")
