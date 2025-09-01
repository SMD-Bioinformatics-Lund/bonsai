"""Internal data models."""

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator, ConfigDict


class ContentType(StrEnum):
    """If email should be rendered as html or in plain text."""

    HTML = "html"
    PLAIN = "plain"


class EmailTemplateContext(BaseModel):
    """Defines the names space for contextual information to be rendered in template.
    
    This is intended to reserve varialbe names to use in the template.
    """

    model_config = ConfigDict(extra="allow")

    user_name: str | None = Field(default=None, examples="Nollan Nollssson", 
                                  description="Recipients full name.")


class EmailApiInput(BaseModel):
    """Input data for sending an email."""

    recipient: list[str]
    subject: str
    template_name: str | None = None
    message: str | None = None
    context: EmailTemplateContext | None = None
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
