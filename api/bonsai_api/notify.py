"""Dispatch email messages using the notification service"""
from enum import StrEnum
import logging
from typing import Any
import requests
from requests.exceptions import HTTPError
from pydantic import BaseModel

LOG = logging.getLogger(__name__)


class ContentType(StrEnum):
    """
    Supported content email types.

    Members:
        HTML: Email should be HTML formatted.
        PLAIN: Email using unformatted text.
    """
    HTML = "html"
    PLAIN = "plain"


class EmailApiInput(BaseModel):
    """Input data for sending an email."""

    recipient: list[str]
    subject: str
    template_name: str | None = None
    message: str | None = None
    context: dict[str, Any] | None = None
    content_type: ContentType = ContentType.PLAIN


def dispatch_email(api_url: str, message: EmailApiInput, timeout: int = 10) -> bool:
    """Dispatch a request to send a email."""

    resp = requests.post(api_url, json=message.model_dump(mode='json'), timeout=timeout)
    try:
        resp.raise_for_status()
    except HTTPError as err:
        LOG.error("Could not send a email message: %s", str(err))
        return False
    return True
