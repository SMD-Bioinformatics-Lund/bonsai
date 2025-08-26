"""Models for integrity reports."""

from enum import StrEnum
import datetime as dt

from pydantic import BaseModel, Field


class InitiatorType(StrEnum):
    """Types of integrity check initiators."""

    USER = "user"
    SYSTEM = "system"
    
class IntegrityReport(BaseModel):
    """Report on the integrity of signature files in the repository."""

    timestamp: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.UTC), description="UTC timestamp of the report generation")
    initiated_by: InitiatorType
    duration: int = Field(..., description="Duration in seconds")
    version: str = Field(..., description="Sourmash version")
    total_records: int
    total_indexed: int
    missing_files: list[str]
    corrupted_files: list[str]
    should_be_indexed: list[str]
    should_not_be_indexed: list[str]