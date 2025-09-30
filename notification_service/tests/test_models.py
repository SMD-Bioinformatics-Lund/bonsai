import pytest

from bonsai_notification.models import ContentType, EmailApiInput


def test_plain_email_requires_message():
    with pytest.raises(ValueError):
        EmailApiInput(
            recipient=["test@example.com"],
            subject="Test",
            content_type=ContentType.PLAIN,
            message=None,
        )


def test_html_email_allows_no_message():
    obj = EmailApiInput(
        recipient=["test@example.com"],
        subject="Test",
        content_type=ContentType.HTML,
        message=None,
    )
    assert obj.content_type == ContentType.HTML
