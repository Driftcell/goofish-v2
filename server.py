import dotenv

from helpers.agiso import AgisoLoginHelper
from helpers.base import LoginState
from helpers.goofish import GoofishLoginHelper

dotenv.load_dotenv()


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from route import AuthRouter, ConfigRouter, ItemRouter, LogRouter, UploadRouter
from route.filter import global_exception_handler
from route.lifespan import lifespan
from route.midware import TokenMiddleware

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
app.add_middleware(TokenMiddleware)

app.add_exception_handler(Exception, handler=global_exception_handler)


app.include_router(LogRouter)
app.include_router(ConfigRouter)
app.include_router(AuthRouter)
app.include_router(ItemRouter)
app.include_router(UploadRouter)

