from enum import StrEnum
from typing import Any
import datetime as dt

from pydantic import BaseModel, ConfigDict, Field


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


class EventCreate(BaseModel):
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

class EventResponse(BaseModel):
    """Response shape for POST /events (202 Accepted)."""
    id: str = Field(..., description="Server-assigned identifier for the event.")


class EventOut(EventCreate):
    """Event as stored + MongoDB '_id' made available as string 'id'."""

    id: str


class PaginatedEventsOut(BaseModel):
    """Paginated response model for events."""

    items: list[EventOut]
    total: int
    limit: int
    skip: int
    has_more: bool
 