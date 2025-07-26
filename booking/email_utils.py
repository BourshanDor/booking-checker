import smtplib
from email.mime.text import MIMEText
import logging

logger = logging.getLogger("opora_checker")


def send_html_email(
    subject,
    html_content,
    from_addr,
    to_addrs,
    smtp_server="smtp.gmail.com",
    smtp_port=587,
    login_user=None,
    login_password=None,
):
    msg = MIMEText(html_content, "html")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs) 

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            if login_user and login_password:
                server.login(login_user, login_password)
            server.send_message(msg)
        logger.info("HTML Email sent successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to send HTML email: {e}")
        return False
