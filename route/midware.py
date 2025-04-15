from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class TokenMiddleware(BaseHTTPMiddleware):
    """
    Token中间件
    
    处理HTTP请求中的令牌，从请求头中提取X-TOKEN并存储到请求状态中供后续处理使用。
    
    Attributes:
        继承自BaseHTTPMiddleware，无额外属性
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        处理HTTP请求的中间件分发方法
        
        从请求头中提取X-TOKEN并将其保存到请求状态中，然后将请求传递给下一个处理器。
        
        Args:
            request (Request): FastAPI请求对象
            call_next (callable): 调用链中的下一个处理器
            
        Returns:
            Response: HTTP响应对象
        """
        token = request.headers.get("X-TOKEN")
        if token:
            request.state.token = token
        response = await call_next(request)
        return response