"""Email integration."""

import smtplib
from email.message import EmailMessage

from .config import EmailConfig, SmtpConfig


def get_smtp_connection(cnf: SmtpConfig) -> smtplib.SMTP:
    """Wrapper to connect to SMTP server using info from config."""

    return smtplib.SMTP(host=cnf.host, port=cnf.port, timeout=cnf.timeout)


def create_email(recipients: list[str], cnf: EmailConfig) -> EmailMessage:
    """Send email using sender information from config."""

    msg = EmailMessage()
    msg["From"] = cnf.sender_name
    msg["Sender"] = cnf.sender
    msg["To"] = ",".join(recipients)

    return msg
