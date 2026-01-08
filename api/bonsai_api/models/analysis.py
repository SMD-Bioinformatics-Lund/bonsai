"""Models for creating and managing analysis results from differnt softwares."""

from enum import StrEnum
from typing import Any
from uuid import UUID
from pydantic import Field
from .base import Timestamps, AllowExtraModelMixin


class CurationStatus(StrEnum):

    PASSED = "passed"
    FAILED = "failed"


class CurationRecord(Timestamps, AllowExtraModelMixin):
    """Manual curation and evaluation of analysis results."""
    id: UUID
    target: str = Field(description="Pointer or id of relevant object.")
    status: CurationStatus
    currated_by: str
    comment: str


class AnalysisResult(Timestamps, AllowExtraModelMixin):
    """Container of analysis results."""

    # meta information
    schema_version: int = 1
    sample_id: str
    analysis_type: str = Field(..., description="The kind of analysis being performed.")
    software: str
    software_version: str | None = None
    pipeline_run_id: str | None = None

    # results
    result: Any = Field(..., description="Formatted analysis result")
    curration: list[CurationRecord] = Field(default_factory=list)

    # created by
    created_by: str | None = None
