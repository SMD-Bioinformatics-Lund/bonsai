"""Tasks exposed to redis."""

import logging

from .config import settings as cnf
from .models import EmailApiInput
from .sender import send_email

LOG = logging.getLogger(__name__)


def queue_send_email(email):
    """Queue a job for sending email."""

    msg_obj = EmailApiInput.model_validate(email)
    LOG.info("Got task to send email to %s", ", ".join(msg_obj.recipients))
    send_email(cnf.sender_email, sender_name=cnf.sender_name, message_obj=msg_obj)
