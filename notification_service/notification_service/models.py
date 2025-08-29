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
        """Check that either message or context has been set"""
        if self.message is not None or self.context is not None:
            raise ValueError(
                "Input must contain either a message or context to be templated."
            )
        return self
