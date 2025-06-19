"""Sample information in database"""

import datetime
from pydantic import Field

from bonsai_models.base import ApiModel
from bonsai_models.constants import (ResistanceTag, TagSeverity, TagType,
                                     VirulenceTag)
from bonsai_models.schema.metadata import InputMetaEntry
from bonsai_models.schema.pipeline.base import PipelineResult
from bonsai_models.schema.qc import SampleQcClassification
from bonsai_models.utils.timestamp import get_timestamp


class Tag(ApiModel):
    """Tag data structure."""

    type: TagType
    label: VirulenceTag | ResistanceTag
    description: str
    severity: TagSeverity


TagList = list[Tag]


class CommentBase(ApiModel):
    """Contianer for comments."""

    username: str = Field(..., min_length=0)
    comment: str = Field(..., min_length=0)
    displayed: bool = True


class CommentInDb(CommentBase):
    """Comment data structure in database."""

    id: int = Field(..., alias="id")
    created_at: datetime.datetime = Field(default_factory=get_timestamp)


class SampleInDb(PipelineResult):
    """Base datamodel for sample data structure"""

    tags: TagList = []
    metadata: list[InputMetaEntry] = []
    qc_status: SampleQcClassification = Field(default_factory=SampleQcClassification)
    # comments and non analytic results
    comments: list[CommentInDb] = []
    location: str | None = Field(None, description="Location id")
    # signature file name
    genome_signature: str | None = Field(None, description="Genome signature name")
    ska_index: str | None = Field(None, description="Ska index path")
    # timestamps
    created_at: datetime.datetime = Field(default_factory=get_timestamp)
    modified_at: datetime.datetime = Field(default_factory=get_timestamp)
