"""Data models and types."""

from pathlib import Path
from datetime import datetime, timezone
from typing import Annotated

from bson import ObjectId
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
SampleIdStr = Annotated[str, StringConstraints(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9._-]+$")]

class SignatureRecord(BaseModel):
    """
    Signature bookkeeping record.

    - `sample_id`: external or internal identifier for the sample/signature
    - `signature_path`: where the signature artifact is stored (filesystem, s3 path, etc.)
    - `checksum`: hex string (default: sha256)
    - `has_been_indexed`: whether the artifact has been indexed
    - `indexed_at`: UTC timestamp when indexing completed
    - `exclude_from_index`: flags records to be skipped by indexers
    - `_id`: MongoDB Document ID (optional, for round-trip)
    - `uploaded_at`: UTC timestamp when the record was created
    """

    # MongoDB `_id` (optional). If you prefer to keep domain model clean, remove this
    # and always use Mongo projection {"_id": 0} in reads.
    id: ObjectId | None = Field(default=None, alias="_id")

    sample_id: SampleIdStr
    signature_path: Path
    checksum: Sha256Hex

    has_been_indexed: bool = False
    indexed_at: datetime | None = None
    exclude_from_index: bool = False

    uploaded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    model_config = ConfigDict(
        populate_by_name=True,  # enables setting/getting by "_id" alias
        use_enum_values=True,
    )

    # ---- serialization helpers --------------------------------------------

    @field_serializer("_id", when_used="json-unless-none")
    def _ser_object_id(self, v: ObjectId | None, _info):
        # If you want ObjectId preserved in Python dicts (not JSON), remove this.
        return str(v) if v is not None else None

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
