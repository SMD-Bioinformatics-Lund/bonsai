

from datetime import datetime
from enum import StrEnum
from pydantic import Field

from bonsai_api.utils import get_timestamp
from .base import AllowExtraModelMixin, Timestamps
from .analysis import SequencingInfo, PipelineRun
from .sample import CommentInDatabase, QcClassification, MetaEntryInDb
from .tags import Tag


class OverallAnalysisStatus(StrEnum):
    NONE = "none"
    PENDING = "pending"
    PARTIAL = "partial"
    COMPLETE = "complete"
    FAILED = "failed"


class ExportState(StrEnum):
    NOT_EXPORTED = "not_exported"
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class ExportStatus(AllowExtraModelMixin):
    """Status of exported document"""

    state: ExportState = ExportState.NOT_EXPORTED
    exported_at: datetime = Field(default_factory=get_timestamp)
    exported_by: str | None = None
    error: str | None = None


class SampleRecordDb(Timestamps, AllowExtraModelMixin):
    """Updated container for sample information."""

    sample_id: str
    sample_name: str | None = None
    lims_id: str | None = None

    tags: list[Tag] = Field(default_factory=list)

    sequencing: SequencingInfo | None = None
    last_pipeline_run: PipelineRun | None = None
    pipeline_runs: list[PipelineRun] = Field(default_factory=list)

    metadata: list[MetaEntryInDb] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    comments: list[CommentInDatabase] = Field(default_factory=list)
    location: str | None = Field(default=None, description="Location id")

    qc_status: QcClassification = Field(default_factory=QcClassification)
    lims_export: list[ExportStatus]

    analysis_status: OverallAnalysisStatus = OverallAnalysisStatus.NONE
