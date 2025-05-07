"""Models for representing various metadata as either input or in the database."""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel


class MetadataTypes(StrEnum):

    STR = "string"
    INT ="integer"
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
    category: str
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