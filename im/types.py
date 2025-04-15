from enum import Enum, auto

from pydantic import BaseModel, Field


class IMTaskType(Enum):
    """
    即时通讯任务类型枚举。
    
    定义了系统可执行的各种任务类型。
    """
    SLEEP = auto()  # 休眠任务
    SENDMSG = auto()  # 发送消息任务
    SENDIMG = auto()  # 发送图片任务
    AIMODEL = auto()  # AI模型处理任务


class Message(BaseModel):
    """
    消息模型类。
    
    表示即时通讯中的一条消息，包含消息的各种属性。
    """
    session_id: str = Field(..., alias="sessionId")  # 会话ID，标识消息所属的会话
    message_id: str = Field(..., alias="messageId")  # 消息ID，唯一标识一条消息
    sender_id: int = Field(..., alias="senderId")  # 发送者ID，标识消息的发送者
    is_my_msg: bool = Field(..., alias="isMyMsg")  # 是否为自己发送的消息
    time_stamp: int = Field(..., alias="timeStamp")  # 消息的时间戳
    content: str = Field(...)  # 消息内容


class IMTask(BaseModel):
    """
    即时通讯任务模型类。
    
    定义了一个需要执行的任务，包含任务类型和上下文信息。
    """
    type_: IMTaskType = Field(...)  # 任务类型
    context: "IMContext" = Field(...)  # 任务上下文，包含执行任务所需的数据


class IMContext(BaseModel):
    """
    即时通讯上下文模型类。
    
    包含执行任务所需的各种上下文信息和数据。
    """
    sender: int | None = None  # 发送者ID，可为空
    session_id: str | None = None  # 会话ID，可为空
    outer_id: str | None = None  # 外部ID，用于关联外部系统，可为空
    messages: list[Message] | None = None  # 消息列表，可为空
    sleep: int | None = None  # 休眠时间（单位：秒），可为空
    text: str | None = None  # 文本内容，可为空
    image: bytes | None = None  # 图片数据，可为空
    next_task: IMTask | None = None  # 下一个需要执行的任务，可为空
