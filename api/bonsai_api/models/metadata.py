"""Models for representing various metadata as either input or in the database."""

from datetime import datetime
import math
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, field_validator


class MetadataTypes(StrEnum):

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

    @field_validator("data", mode="before")
    @classmethod
    def normalize_empty_cells(cls, rows):
        return [["" if isinstance(cell, float) and math.isnan(cell) else cell for cell in row] for row in rows]


InputMetaEntry = DatetimeMetadataEntry | InputTableMetadata | GenericMetadataEntry
MetaEntryInDb = DatetimeMetadataEntry | TableMetadataInDb | GenericMetadataEntry
def normalize_metadata_tables(entries):
    """Read both stored tables and CSV inputs accepted by older sample uploads."""
    from bonsai_api.io import parse_metadata_table

    return [
        parse_metadata_table(entry=entry)
        if isinstance(entry, InputTableMetadata)
        else parse_metadata_table(entry=InputTableMetadata.model_validate(entry))
        if isinstance(entry, dict) and entry.get("type") == "table" and "value" in entry
        else entry
        for entry in entries
    ]


MetaEntriesInDb = Annotated[list[MetaEntryInDb], BeforeValidator(normalize_metadata_tables)]
