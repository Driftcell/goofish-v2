import os
from email.message import EmailMessage

import aiosmtplib
import structlog

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

async def email_report(to: str, content: str):
    # 创建邮件消息
    message = EmailMessage()
    message["From"] = os.environ.get("SMTP_USER")
    message["To"] = to
    message["Subject"] = f"Goofish System Report"
    message.set_content(content)

    # 邮件服务器配置
    smtp_server = os.environ.get("SMTP_SERVER")
    smtp_port = os.environ.get("SMTP_PORT")
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASS")

    assert smtp_server is not None, "SMTP_SERVER is not set"
    assert smtp_port is not None, "SMTP_PORT is not set"
    assert smtp_user is not None, "SMTP_USER is not set"
    assert smtp_password is not None, "SMTP_PASS is not set"

    try:
        await aiosmtplib.send(
            message,
            hostname=smtp_server,
            port=int(smtp_port),
            username=smtp_user,
            password=smtp_password,
            use_tls=True,
        )
    except Exception as e:
        logger.error("Failed to send email", error=str(e))