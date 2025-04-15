"""
服务器主模块

该模块初始化 FastAPI 应用程序，配置日志系统，设置中间件，
并注册各种路由处理程序。
"""
import sys
import dotenv

# 加载环境变量
dotenv.load_dotenv()


import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 导入路由和中间件组件
from route import AuthRouter, ConfigRouter, ItemRouter, LogRouter, UploadRouter
from route.filter import global_exception_handler
from route.lifespan import lifespan
from route.log import sse_processor
from route.midware import TokenMiddleware
import logging

# 创建结构化日志记录器
logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

# 配置结构化日志系统
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,  # 根据日志级别过滤
        structlog.stdlib.add_log_level,    # 添加日志级别到输出
        structlog.stdlib.add_logger_name,  # 添加记录器名称
        structlog.processors.TimeStamper(fmt="iso"),  # 添加 ISO 格式时间戳
        structlog.processors.StackInfoRenderer(),     # 渲染堆栈信息
        structlog.processors.format_exc_info,         # 格式化异常信息
        sse_processor,                                # 自定义的 SSE 处理器
        structlog.dev.ConsoleRenderer(colors=True),   # 启用彩色控制台输出
    ],
    context_class=dict,                   # 使用字典作为上下文类
    logger_factory=structlog.stdlib.LoggerFactory(),  # 使用标准库日志工厂
    wrapper_class=structlog.stdlib.BoundLogger,       # 使用绑定日志记录器
    cache_logger_on_first_use=True,                   # 首次使用时缓存日志记录器
)

# 配置标准库日志
logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=logging.INFO,
)

# 创建 FastAPI 应用实例，设置生命周期管理
app = FastAPI(lifespan=lifespan)

# 添加 CORS 中间件，允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # 允许所有来源
    allow_methods=["*"],     # 允许所有 HTTP 方法
    allow_headers=["*"],     # 允许所有 HTTP 头
    allow_credentials=True,  # 允许发送凭据
)

# 添加自定义 Token 中间件，处理认证
app.add_middleware(TokenMiddleware)

# 添加全局异常处理器
app.add_exception_handler(Exception, handler=global_exception_handler)

# 注册各种功能路由
app.include_router(LogRouter)     # 日志相关路由
app.include_router(ConfigRouter)  # 配置相关路由
app.include_router(AuthRouter)    # 认证相关路由
app.include_router(ItemRouter)    # 项目相关路由
app.include_router(UploadRouter)  # 上传相关路由
