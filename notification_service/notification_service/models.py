"""Internal data models."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, model_validator


class ContentType(StrEnum):
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

    @model_validator(mode="after")
    def check_has_message(self):
        """Check that the message been set for plain emails."""
        if self.message is None and self.content_type == ContentType.PLAIN:
            raise ValueError(
                "A message must be provided when sending a email in plain text."
            )
        return self

    def check_has_message_or_context(self):
        """Check that either message or context has been set"""
        if self.message is None and self.context is None:
            raise ValueError(
                "A message must be provided when sending a email in plain text."
            )
        return self
