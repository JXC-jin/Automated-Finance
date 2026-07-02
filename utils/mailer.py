"""
utils/mailer.py
邮件发送工具
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List

logger = logging.getLogger(__name__)


def send_html_email(
    sender: str,
    password: str,
    recipients: List[str],
    subject: str,
    html_body: str,
    smtp_host: str = "smtp.qq.com",
    smtp_port: int = 465,
) -> bool:
    """
    发送 HTML 邮件
    
    Args:
        sender: 发件人邮箱
        password: SMTP 授权码
        recipients: 收件人列表
        subject: 邮件主题
        html_body: HTML 正文
        smtp_host: SMTP 服务器
        smtp_port: SMTP 端口
    
    Returns:
        bool: 发送是否成功
    """
    recipients = [recipient.strip() for recipient in recipients if recipient.strip()]
    if not sender or not password or not recipients:
        logger.error("邮件发送失败: 发件人、SMTP 授权码或收件人为空")
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject

    html_part = MIMEText(html_body, "html", "utf-8")
    msg.attach(html_part)

    ports = [smtp_port]
    for fallback_port in (587, 465):
        if fallback_port not in ports:
            ports.append(fallback_port)

    for port in ports:
        server = None
        try:
            logger.info(f"尝试通过 {smtp_host}:{port} 发送邮件")
            if port == 465:
                server = smtplib.SMTP_SSL(smtp_host, port, timeout=30)
            else:
                server = smtplib.SMTP(smtp_host, port, timeout=30)
                server.ehlo()
                server.starttls()

            server.ehlo()
            server.login(sender, password)
            server.sendmail(sender, recipients, msg.as_string())
            server.quit()

            logger.info(f"✅ 邮件发送成功: {recipients}")
            return True

        except Exception as e:
            logger.warning(f"{smtp_host}:{port} 发送失败: {e}")
            if server is not None:
                try:
                    server.quit()
                except Exception:
                    pass

    logger.error("❌ 邮件发送失败: 所有 SMTP 连接方式均失败")
    return False
