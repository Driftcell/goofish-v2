from enum import Enum, auto

from pydantic import BaseModel, Field


class IMTaskType(Enum):
    SLEEP = auto()
    SENDMSG = auto()
    SENDIMG = auto()
    AIMODEL = auto()


class Message(BaseModel):
    session_id: str = Field(..., alias="sessionId")
    message_id: str = Field(..., alias="messageId")
    sender_id: int = Field(..., alias="senderId")
    is_my_msg: bool = Field(..., alias="isMyMsg")
    time_stamp: int = Field(..., alias="timeStamp")
    content: str = Field(...)


class IMTask(BaseModel):
    type_: IMTaskType = Field(...)
    context: "IMContext" = Field(...)


class IMContext(BaseModel):
    sender: int | None = None
    session_id: str | None = None
    outer_id: str | None = None
    messages: list[Message] | None = None
    sleep: int | None = None
    text: str | None = None
    image: bytes | None = None
    next_task: IMTask | None = None
