from unittest.mock import MagicMock, patch

import pytest

from notification_service.models import (ContentType, EmailApiInput,
                                         EmailTemplateContext)
from notification_service.services.email import send_email


class DummyTemplate:
    def render(self, **kwargs):
        return "<html><body>{}</body></html>".format(kwargs.get("message", ""))


class DummyTemplateRepo:
    @classmethod
    def get_template(cls, name=None):
        return DummyTemplate()


def test_send_email_plain():
    smtp_mock = MagicMock()
    msg = EmailApiInput(
        recipient=["test@example.com"],
        subject="Test",
        content_type=ContentType.PLAIN,
        message="Hello world",
    )
    send_email(
        sender_email="noreply@example.com",
        sender_name="Notification",
        message_obj=msg,
        smtp_conn=smtp_mock,
        template_repo=DummyTemplateRepo,
    )
    # Check that set_content was called with plain text
    sent_msg = smtp_mock.send_message.call_args[0][0]
    assert sent_msg.get_content_type() == "text/plain"
    assert "Hello world" in sent_msg.get_content()


def test_send_email_html():
    smtp_mock = MagicMock()
    ctx = EmailTemplateContext(foo="bar")
    msg = EmailApiInput(
        recipient=["test@example.com"],
        subject="Test",
        content_type=ContentType.HTML,
        message="Hello HTML",
        template_name="dummy",
        context=ctx,
    )
    send_email(
        sender_email="noreply@example.com",
        sender_name="Notification",
        message_obj=msg,
        smtp_conn=smtp_mock,
        template_repo=DummyTemplateRepo,
    )
    sent_msg = smtp_mock.send_message.call_args[0][0]
    assert sent_msg.get_content_type() == "text/html"
    assert "<html>" in sent_msg.get_content()
    assert "Hello HTML" in sent_msg.get_content()
