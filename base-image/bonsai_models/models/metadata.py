"""Metadata models."""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel

from .base import RWModel


class MetadataTypes(StrEnum):
    """Valid datatypes for metadata records."""

    STR = "string"
    INT = "integer"
    FLOAT = "float"


class GenericMetadataEntry(BaseModel):
    """Container of basic metadata information"""

    fieldname: str
    value: str | int | float
    category: str
    type: MetadataTypes


class DatetimeMetadataEntry(BaseModel):
    """Container of basic metadata information"""

    fieldname: str
    value: datetime
    category: str
    type: Literal["datetime"]


class InputTableMetadata(BaseModel):
    """Metadata table info recieved by API."""

    fieldname: str
    value: str
    category: str = "general"
    type: Literal["table"] = "table"


class TableMetadataInDb(BaseModel):
    """Metadata table stored in database."""

    fieldname: str
    columns: list[str] = []
    index: list[str] = []
    data: list[list[str | int | float | datetime]]
    category: str
    type: Literal["table"] = "table"


InputMetaEntry = DatetimeMetadataEntry | InputTableMetadata | GenericMetadataEntry
MetaEntryInDb = DatetimeMetadataEntry | TableMetadataInDb | GenericMetadataEntry
MetaEntriesInDb = list[MetaEntryInDb]


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
    instrument: str | None = None
    method: dict[str, str] = {}
    date: datetime | None = None


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
