"""Models for integrity reports."""

import datetime as dt
from enum import StrEnum

from pydantic import BaseModel, Field, computed_field


class InitiatorType(StrEnum):
    """Types of integrity check initiators."""

    USER = "user"
    SYSTEM = "system"


class ReportStatus(StrEnum):
    """Status codes for a report."""

    WARNING = "warning"
    ERROR = "error"


class IntegrityReport(BaseModel):
    """Report on the integrity of signature files in the repository."""

    timestamp: dt.datetime = Field(
        default_factory=lambda: dt.datetime.now(dt.UTC),
        description="UTC timestamp of the report generation",
    )
    initiated_by: InitiatorType
    duration: int = Field(..., description="Duration in seconds")
    version: str = Field(..., description="Sourmash version")
    total_records: int
    total_indexed: int
    missing_files: list[str]
    corrupted_files: list[str]
    should_be_indexed: list[str]
    should_not_be_indexed: list[str]

    @computed_field
    @property
    def has_errors(self) -> bool:
        """True if any integrity errors were found."""
        return bool(self.missing_files or self.corrupted_files)

    @computed_field
    @property
    def error_count(self) -> int:
        """How many error instances were found (missing + corrupted)."""
        return len(self.missing_files) + len(self.corrupted_files)

    @computed_field
    @property
    def has_warnings(self) -> bool:
        """True if there are indexing mismatches (non-fatal issues)."""
        return bool(self.should_be_indexed or self.should_not_be_indexed)
