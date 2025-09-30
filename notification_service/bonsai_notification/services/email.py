"""Sending notificaitons."""

import smtplib
from email.message import EmailMessage

from bonsai_notification.config import SmtpConfig
from bonsai_notification.models import ContentType, EmailApiInput
from .templates import TemplateRepository


def get_smtp_connection(cnf: SmtpConfig) -> smtplib.SMTP:
    """Wrapper to connect to SMTP server using info from config."""
    if cnf.host is None:
        raise ValueError("No host specified for email connection.")
    return smtplib.SMTP(host=cnf.host, port=cnf.port, timeout=cnf.timeout)


def send_email(
    sender_email: str,
    sender_name: str,
    message_obj: EmailApiInput,
    template_repo: TemplateRepository,
    smtp_conn: smtplib.SMTP | None = None,
) -> None:
    """Send a email."""
    if smtp_conn is None:
        raise RuntimeError("No SMTP connection passed to function.")
    with smtp_conn as conn:
        # create new mail
        mail = EmailMessage()
        mail["From"] = sender_name
        mail["Sender"] = sender_email
        mail["To"] = ",".join(message_obj.recipient)
        mail["Subject"] = message_obj.subject

        # render template if template name is set
        if message_obj.content_type == ContentType.PLAIN:
            mail.set_content(message_obj.message)
        else:
            template = template_repo.get_template(message_obj.template_name)
            # pass context to template
            html_content = template.render(
                sender_name=sender_name,
                **message_obj.model_dump(exclude=set(["template_name", "content_type"]))
            )
            mail.set_content(html_content, subtype="html")
        conn.send_message(mail)
