"""Definition of events that are logged."""

import datetime as dt
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class EventSeverity(StrEnum):
    """Event severity level."""

    DEBUG = "debug"
    INFO = "info"
    WARN = "warning"
    ERROR = "error"


class SourceType(StrEnum):
    """origin of the actor or subject."""

    USR = "user"
    SYS = "system"


class Actor(BaseModel):
    """Entity that triggered or logged the event."""
    type: SourceType = Field(..., description="Type of actor (user or system).", examples=["user"])
    id: str = Field(..., description="Unique identifier of the actor.", examples=["user_123", "system_daemon"])


class Subject(BaseModel):
    """Entity that the event is about (target)."""
    type: SourceType = Field(..., description="Type of subject (user or system).", examples=["system"])
    id: str = Field(..., description="Unique identifier of the subject.", examples=["sample_456", "group_789"])


class Event(BaseModel):
    """
    Represents an audit trail event for tracking significant actions across services.

    Attributes:
        source_service: Name of the service that emitted the event.
        event_type: Type or category of the event (e.g., CREATE_USER, DELETE_GROUP).
        occurred_at: UTC timestamp when the event occurred.
        severity: Severity level of the event (debug, info, warning, error).
        actor: Who initiated or logged the event.
        subject: The entity that the event is about.
        metadata: Optional key-value metadata for additional context.
    """

    source_service: str = Field(
        ...,
        description="Name of the service that emitted the event.",
        examples=["minhash_service", "bonsai_api"]
    )
    event_type: str = Field(
        ...,
        description="Type or category of the event.",
        examples=["CREATE_USER", "DELETE_GROUP"]
    )
    occurred_at: dt.datetime = Field(
        default_factory=lambda: dt.datetime.now(dt.timezone.utc),
        alias="occurred_at",
        description="UTC timestamp when the event occurred."
    )
    severity: EventSeverity = Field(
        default=EventSeverity.INFO,
        description="Severity level of the event."
    )
    actor: Actor = Field(..., description="Entity that triggered or logged the event.")
    subject: Subject = Field(..., description="Entity that the event is about.")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional key-value metadata for additional context.",
        examples=[{"ip": "192.168.1.10", "session_id": "abc123"}]
    )

    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True  # allows using `occurred_at` in Python while serializing as `occurred_at`
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
    occurred_after: dt.datetime | None = Field(default=None, description="Include samples that occurred after")
    occurred_before: dt.datetime | None = Field(default=None, description="Include samples that occurred before")

    model_config = ConfigDict(extra="ignore")


    @field_serializer("occurred_after", "occurred_before")
    def _ser_utc(cls, val: dt.datetime | None) -> str | None:
        """Ensure that occurred before and after are in UTC format."""
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
 