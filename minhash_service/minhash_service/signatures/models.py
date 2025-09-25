"""Models"""

import datetime as dt
from enum import StrEnum
from pathlib import Path
from typing import Annotated

from pydantic import (BaseModel, ConfigDict, Field, StringConstraints,
                      field_serializer, field_validator)
from sourmash.signature import FrozenSourmashSignature, SourmashSignature

from minhash_service.core.models import SampleIdStr

SourmashSignatures = list[SourmashSignature | FrozenSourmashSignature]


class IndexFormat(StrEnum):
    """Valid index formats."""

    SBT = "SBT"
    ROCKSDB = "rocksdb"


class SignatureName(BaseModel):
    """Signature name"""

    name: str
    filename: str


# Constrain `checksum` to md5 hex; adjust if you support other algos.
Md5Hex = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{32}$")]
Sha256Hex = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]


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
    file_checksum: Sha256Hex
    signature_checksum: Md5Hex

    has_been_indexed: bool = False
    indexed_at: dt.datetime | None = None
    exclude_from_analysis: bool = False

    marked_for_deletion: bool = Field(
        default=False, description="Flag to mark record for deletion"
    )

    uploaded_at: dt.datetime = Field(
        default_factory=lambda: dt.datetime.now(dt.timezone.utc)
    )

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
    def _ensure_indexed_at_is_aware(cls, val):
        if val is None:
            return val
        if isinstance(val, dt.datetime) and val.tzinfo is None:
            return val.replace(tzinfo=dt.timezone.utc)
        return val

    @field_validator("uploaded_at", mode="before")
    @classmethod
    def _ensure_uploaded_at_is_aware(cls, val):
        if val is None:
            return dt.datetime.now(dt.timezone.utc)
        if isinstance(val, dt.datetime) and val.tzinfo is None:
            return val.replace(tzinfo=dt.timezone.utc)
        return val
