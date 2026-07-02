"""
utils/mailer.py
邮件发送工具
"""
import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List

logger = logging.getLogger(__name__)


def _login_candidates(sender: str, login_user: str = "") -> List[tuple[str, str]]:
    sender = sender.strip()
    login_user = (login_user or "").strip()
    candidates = []
    if login_user:
        candidates.append(("配置账号", login_user))
    candidates.append(("发件邮箱", sender))
    if sender.lower().endswith("@qq.com"):
        candidates.append(("QQ号", sender.split("@", 1)[0]))

    seen = set()
    result = []
    for label, login_name in candidates:
        if login_name not in seen:
            seen.add(login_name)
            result.append((label, login_name))
    return result


def _describe_login_error(host: str, ports: List[int], login_stage_failures: int) -> str:
    if host == "smtp.qq.com" and login_stage_failures:
        return (
            f"QQ SMTP 登录失败，已尝试端口 {ports}。请重点检查 PASSWORD 是否为 QQ 邮箱"
            "“SMTP 授权码”（不是 QQ 登录密码），以及 QQ/MAIL/PASSWORD 是否属于同一个已开启 SMTP 的邮箱账号。"
        )
    return "所有 SMTP 连接方式均失败"


def send_html_email(
    sender: str,
    login_user: str,
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
    login_user = (login_user or sender).strip()
    password = "".join((password or "").split())
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

    local_hostname = sender.split("@")[-1] if "@" in sender else "localhost"
    context = ssl.create_default_context()

    login_stage_failures = 0
    for port in ports:
        for login_label, login_name in _login_candidates(sender, login_user):
            server = None
            stage = "connect"
            try:
                logger.info(f"尝试通过 {smtp_host}:{port} 发送邮件，登录方式：{login_label}")
                if port == 465:
                    server = smtplib.SMTP_SSL(
                        smtp_host,
                        port,
                        local_hostname=local_hostname,
                        timeout=30,
                        context=context,
                    )
                else:
                    server = smtplib.SMTP(
                        smtp_host,
                        port,
                        local_hostname=local_hostname,
                        timeout=30,
                    )
                    stage = "ehlo-before-starttls"
                    server.ehlo()
                    stage = "starttls"
                    server.starttls(context=context)

                stage = "ehlo"
                server.ehlo()
                stage = "login"
                server.login(login_name, password)
                stage = "sendmail"
                server.sendmail(sender, recipients, msg.as_string())
                stage = "quit"
                server.quit()

                logger.info(f"✅ 邮件发送成功: {recipients}")
                return True

            except Exception as e:
                if stage == "login":
                    login_stage_failures += 1
                logger.warning(f"{smtp_host}:{port} 使用{login_label}在 {stage} 阶段发送失败: {e}")
                if server is not None:
                    try:
                        server.quit()
                    except Exception:
                        pass

    logger.error(f"❌ 邮件发送失败: {_describe_login_error(smtp_host, ports, login_stage_failures)}")
    return False
