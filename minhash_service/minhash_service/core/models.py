"""Data models that are shared across the app."""

import datetime as dt
from enum import StrEnum
from typing import Annotated

from pydantic import (BaseModel, ConfigDict, Field, StringConstraints,
                      field_validator)

SampleIdStr = Annotated[
    str, StringConstraints(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9._-]+$")
]


class EventType(StrEnum):
    """Types of audit trail events."""

    UPLOAD = "upload"
    INDEX = "index"
    DELETE = "delete"
    ERROR = "error"
    OTHER = "other"


class Event(BaseModel):
    """
    Audit trail event.

    - `event_type`: type of event (upload, index, delete, error, other)
    - `sample_id`: associated sample_id (if any)
    - `timestamp`: UTC timestamp when the event occurred
    - `details`: optional free-form details about the event
    """

    event_type: EventType
    sample_id: SampleIdStr | None = None
    timestamp: dt.datetime = Field(
        default_factory=lambda: dt.datetime.now(dt.timezone.utc)
    )
    details: str | None = None
    user_id: str | None = None
    metadata: dict[str, str] | None = None

    model_config = ConfigDict(
        use_enum_values=True,
    )

    # ---- validators ---------------------------------------------------------

    @field_validator("timestamp", mode="before")
    @classmethod
    def _ensure_timestamp_is_aware(cls, v):
        if v is None:
            return dt.datetime.now(dt.timezone.utc)
        if isinstance(v, dt.datetime) and v.tzinfo is None:
            return v.replace(tzinfo=dt.timezone.utc)
        return v
