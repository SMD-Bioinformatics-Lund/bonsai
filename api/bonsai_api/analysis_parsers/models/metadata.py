"""Metadata models."""

from datetime import datetime
from enum import StrEnum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_serializer
from typing_extensions import Annotated

from .base import FilePath, RWModel


class MetadataTypes(StrEnum):

    STR = "string"
    INT = "integer"
    FLOAT = "float"


class StrMetadataEntry(BaseModel):
    """Container of basic metadata information"""

    fieldname: str
    value: str
    category: str = "general"
    type: Literal[MetadataTypes.STR]


class IntMetadataEntry(BaseModel):
    """Container of basic metadata information"""

    fieldname: str
    value: int
    category: str = "general"
    type: Literal[MetadataTypes.INT]


class FloatMetadataEntry(BaseModel):
    """Container of basic metadata information"""

    fieldname: str
    value: int
    category: str = "general"
    type: Literal[MetadataTypes.FLOAT]


class DatetimeMetadataEntry(BaseModel):
    """Container of basic metadata information"""

    fieldname: str
    value: datetime
    category: str = "general"
    type: Literal["datetime"]

    @field_serializer("value")
    def serialize_datetime(self, date: datetime) -> str:
        """Serialize datetime object as string."""
        return date.isoformat()


class TableMetadataEntry(BaseModel):
    """Container of basic metadata information"""

    fieldname: str
    value: FilePath | str
    category: str = "general"
    type: Literal["table"]


MetaEntry = Annotated[
    TableMetadataEntry
    | DatetimeMetadataEntry
    | StrMetadataEntry
    | IntMetadataEntry
    | FloatMetadataEntry,
    Field(discriminator="type"),
]


class SoupType(StrEnum):
    """Type of software of unkown provenance."""

    DB = "database"
    SW = "software"


class SoupVersion(BaseModel):
    """Version of Software of Unknown Provenance."""

    name: str
    version: str
    type: SoupType


class SequencingInfo(RWModel):
    """Information on the sample was sequenced."""

    run_id: str
    platform: str
    instrument: Optional[str]
    method: dict[str, str] = {}
    date: datetime | None


class PipelineInfo(RWModel):
    """Information on the sample was analysed."""

    pipeline: str
    version: str
    commit: str
    analysis_profile: list[str]
    assay: str
    release_life_cycle: str
    configuration_files: list[str]
    workflow_name: str
    command: str
    softwares: list[SoupVersion]
    date: datetime
