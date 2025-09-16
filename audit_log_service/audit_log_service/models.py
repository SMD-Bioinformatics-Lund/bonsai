"""Definition of events that are logged."""

import datetime as dt
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class EventSeverity(StrEnum):
    """Event severity."""

    DEBUG = "debug"
    INFO = "info"
    WARN = "warning"
    ERROR = "error"


class SourceType(StrEnum):

    USR = "user"
    SYS = "system"


class Actor(BaseModel):
    """Records who logged the event."""

    type: SourceType
    id: str


class Subject(BaseModel):
    """What was the targeted of the event."""

    type: SourceType
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


class EventOut(Event):
    """Event as stored + MongoDB '_id' made available as string 'id'."""

    id: str


class EventFilter(BaseModel):
    """Filters for listing events. 
    
    All fields are optional; only provided filters are applied.
    """
    severities: list[str] | None = Field(default=None, examples=["info", "errors"])         # e.g. ["info","error"]
    event_types: list[str] | None = Field(default=None, examples=["CREATE_USER"])         # e.g. ["CREATE_USER"]
    source_services: list[str] | None = Field(default=None, examples=["bonsai_api", "minhash_service"])
    actor_type: SourceType | None = None
    actor_id: str | None = None
    subject_type: SourceType | None = None
    subject_id: str | None = None
    occured_after: dt.datetime | None = Field(default=None, description="Include samples that occured after")
    occured_before: dt.datetime | None = Field(default=None, description="Include samples that occured before")

    model_config = ConfigDict(extra="ignore")


    @field_serializer("occured_after", "occured_before")
    def _ser_utc(cls, val: dt.datetime | None) -> str | None:
        """Ensure that occured before and after are in UTC format."""
        if val is None:
            return None
        # emit RFC3339 with trailing Z
        iso = val.astimezone(dt.timezone.utc).isoformat()
        return iso.replace("+00:00", "Z")


class PaginatedEvents(BaseModel):
    """Paginated response model for events."""

    items: list[EventOut]
    total: int
    limit: int
    skip: int
    has_more: bool
 