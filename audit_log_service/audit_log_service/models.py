"""Definition of events that are logged."""

import datetime as dt
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class EventSeverity(StrEnum):
    """Event severity."""

    DEBUG = "debug"
    INFO = "info"
    WARN = "warning"
    ERROR = "error"


class Actor(BaseModel):
    """Records who logged the event."""

    type: Literal["user", "system"]
    id: str


class Subject(BaseModel):
    """What was the targeted of the event."""

    type: Literal["user", "system"]
    id: str


class Event(BaseModel):
    """
    Audit trail event.

    - `event_type`: type of event (upload, index, delete, error, other)
    - `sample_id`: associated sample_id (if any)
    - `timestamp`: UTC timestamp when the event occurred
    - `details`: optional free-form details about the event
    """

    source_service: str = Field(..., description="Name of the service that emitted the event", examples=["minhash_service", "bonsai_api"])
    event_type: str = Field(..., description="", examples=["CREATE_USER", "DELETE_GROUP"])
    occured_at: dt.datetime = Field(
        default_factory=lambda: dt.datetime.now(dt.timezone.utc)
    )
    severity: EventSeverity = Field(default=EventSeverity.INFO)
    actor: Actor = Field(..., description="Who logged the event.")
    subject: Subject = Field(..., description="What was the event about")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Optional key-value metadata")

    model_config = ConfigDict(
        use_enum_values=True,
    )
