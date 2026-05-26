import os
import smtplib
from email.message import EmailMessage
from email.policy import SMTP


def send_activation_email(email: str, activation_link: str) -> None:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from_email = os.getenv("SMTP_FROM_EMAIL", smtp_username or "")
    smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    smtp_timeout = float(os.getenv("SMTP_TIMEOUT_SECONDS", "10"))

    if not smtp_host or not smtp_from_email:
        raise RuntimeError("SMTP_HOST and SMTP_FROM_EMAIL must be configured")

    message = EmailMessage(policy=SMTP.clone(max_line_length=1000))
    message["Subject"] = "Activate your account"
    message["From"] = smtp_from_email
    message["To"] = email
    message.set_content(
        "Please activate your account by opening this link:\n\n"
        f"{activation_link}\n\n"
        "If you did not create this account, you can ignore this email."
    )

    with smtplib.SMTP(smtp_host, smtp_port, timeout=smtp_timeout) as smtp:
        if smtp_use_tls:
            smtp.starttls()
        if smtp_username and smtp_password:
            smtp.login(smtp_username, smtp_password)
        smtp.send_message(message)
