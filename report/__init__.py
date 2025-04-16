import os
from email.message import EmailMessage

import aiosmtplib
import structlog

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

async def email_report(to: str, content: str):
    """
    发送系统报告邮件。

    参数:
        to (str): 收件人邮箱地址
        content (str): 邮件正文内容

    异步:
        通过SMTP服务器发送邮件，如果发送失败则记录错误日志。
    """
    # 创建邮件消息对象
    message = EmailMessage()
    message["From"] = os.environ.get("SMTP_USER")
    message["To"] = to
    message["Subject"] = f"Goofish System Report"
    message.set_content(content)

    # 获取邮件服务器配置
    smtp_server = os.environ.get("SMTP_SERVER")
    smtp_port = os.environ.get("SMTP_PORT")
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASS")

    # 检查SMTP相关环境变量是否已设置
    assert smtp_server is not None, "SMTP_SERVER 未设置"
    assert smtp_port is not None, "SMTP_PORT 未设置"
    assert smtp_user is not None, "SMTP_USER 未设置"
    assert smtp_password is not None, "SMTP_PASS 未设置"

    try:
        # 发送邮件
        await aiosmtplib.send(
            message,
            hostname=smtp_server,
            port=int(smtp_port),
            username=smtp_user,
            password=smtp_password,
            use_tls=True,
        )
    except Exception as e:
        # 发送失败时记录错误日志
        logger.error("发送邮件失败", error=str(e))