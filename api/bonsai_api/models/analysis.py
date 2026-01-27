"""Models for creating and managing analysis results from differnt softwares."""

from enum import StrEnum
from typing import Any
import uuid_utils as uuid
from pydantic import BaseModel, Field
from .base import Timestamps, AllowExtraModelMixin

from prp.parse.models.base import ParserOutput as PRPParserOutput
from prp.parse.models.enums import AnalysisType as PrpAnalysisType
from prp.parse.models.enums import AnalysisSoftware as PrpAnalysisSoftware


class CurationStatus(StrEnum):

    PASSED = "passed"
    FAILED = "failed"


class CurationRecord(Timestamps, AllowExtraModelMixin):
    """Manual curation and evaluation of analysis results."""
    id: str = Field(description="UUIDv7 string")
    target: str = Field(description="Pointer or id of relevant object.")
    status: CurationStatus
    currated_by: str
    comment: str


class ResultStatus(StrEnum):
    PARSED = "parsed"
    EMPTY = "empty"
    ABSENT = "absent"
    SKIPPED = "skipped"
    ERROR = "error"


class Envelope(BaseModel):
    """Storage-friendly envelope (mirrors PRP’s ResultEnvelope)."""
    status: ResultStatus
    value: Any | None = None
    reason: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class AnalysisResult(Timestamps, AllowExtraModelMixin):
    """Container of analysis results."""

    # meta information
    schema_version: int = 1
    sample_id: str
    software: str
    software_version: str
    pipeline_run_id: str | None = None
    database: str | None = None  # e.g., for AMR databases, cgMLST schemas or kraken DBs

    # results
    envelopes: dict[str, Envelope] = Field(default_factory=dict, description="Formatted analysis result")
    meta: dict[str, Any] = Field(default_factory=dict)

    # created by
    created_by: str | None = None
