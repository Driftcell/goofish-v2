from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class TokenMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        token = request.headers.get("X-TOKEN")
        if token:
            request.state.token = token
        response = await call_next(request)
        return response