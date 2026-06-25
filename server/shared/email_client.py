import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings


async def send_email(to: str, subject: str, html: str) -> bool:
    """
    发送 HTML 邮件。
    对应 NestJS EmailService.sendEmail。
    """
    try:
        message = MIMEMultipart("alternative")
        message["From"] = settings.email_from
        message["To"] = to
        message["Subject"] = subject
        message.attach(MIMEText(html, "html"))

        await aiosmtplib.send(
            message,
            hostname=settings.email_host,
            port=settings.email_port,
            use_tls=settings.email_use_ssl,
            username=settings.email_user,
            password=settings.email_password,
        )
        return True
    except Exception as e:
        print(f"Email send error: {e}")
        return False
