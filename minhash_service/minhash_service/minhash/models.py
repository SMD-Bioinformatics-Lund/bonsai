"""Data models and types."""

from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_serializer,
    field_validator,
)

Signatures = list[dict[str, int | list[int]]]
SignatureEntry = dict[str, str | Signatures]
SignatureFile = list[SignatureEntry]


class SignatureName(BaseModel):
    """Signature name"""

    name: str
    filename: str


class SimilarSignature(BaseModel):  # pydantic: disable=too-few-public-methods
    """Container for similar signature result"""

    sample_id: str
    similarity: float


SimilarSignatures = list[SimilarSignature]


# Constrain `checksum` to sha256 hex; adjust if you support other algos.
Sha256Hex = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
SampleIdStr = Annotated[
    str, StringConstraints(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9._-]+$")
]


class SignatureRecord(BaseModel):
    """
    Signature bookkeeping record.

    - `sample_id`: external or internal identifier for the sample/signature
    - `signature_path`: where the signature artifact is stored (filesystem, s3 path, etc.)
    - `checksum`: hex string (default: sha256)
    - `has_been_indexed`: whether the artifact has been indexed
    - `indexed_at`: UTC timestamp when indexing completed
    - `exclude_from_analysis`: flags records to be skipped by indexers and analysis
    - `_id`: MongoDB Document ID (optional, for round-trip)
    - `uploaded_at`: UTC timestamp when the record was created
    """

    version: int = Field(default=1, description="Record schema version")
    sample_id: SampleIdStr
    signature_path: Path
    checksum: Sha256Hex

    has_been_indexed: bool = False
    indexed_at: datetime | None = None
    exclude_from_analysis: bool = False

    marked_for_deletion: bool = Field(default=False, description="Flag to mark record for deletion")

    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        populate_by_name=True,  # enables setting/getting by "_id" alias
        use_enum_values=True,
    )

    # ---- serialization helpers --------------------------------------------

    @field_serializer("signature_path")
    def _ser_path(self, v: Path, _info) -> str:
        # Explicitly store Paths as strings in Mongo
        return str(v)

    # ---- validators ---------------------------------------------------------

    @field_validator("indexed_at", mode="before")
    @classmethod
    def _ensure_indexed_at_is_aware(cls, v):
        if v is None:
            return v
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

    @field_validator("uploaded_at", mode="before")
    @classmethod
    def _ensure_uploaded_at_is_aware(cls, v):
        if v is None:
            return datetime.now(timezone.utc)
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


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
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
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
            return datetime.now(timezone.utc)
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v
