"""Sample information in database"""

import datetime
from typing import Literal
from pydantic import Field

from bonsai_models.base import ApiModel
from bonsai_models.constants import (ResistanceTag, TagSeverity, TagType,
                                     VirulenceTag)
from bonsai_models.schema.metadata import InputMetaEntry
from bonsai_models.schema.pipeline.base import CgmlstResultIndex, EmmResultIndex, LineageResultIndex, MlstResultIndex, PipelineResult, SpatyperResultIndex
from bonsai_models.schema.pipeline.metadata import PipelineInfo, SequencingInfo
from bonsai_models.schema.
from bonsai_models.utils.timestamp import get_timestamp

SCHEMA_VERSION: int = 2


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

    schema_version: Literal[2] = SCHEMA_VERSION
    # basic sample info
    sample_id: str = Field(..., alias="sampleId", min_length=3, max_length=100)
    sample_name: str
    lims_id: str

    # database specific fields
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

    # analysis metadata and result
    sequencing: SequencingInfo
    pipeline: PipelineInfo
    qc: list[QcMethodIndex] = Field(...)
    species_prediction: list[SppMethodIndex] = Field(..., alias="speciesPrediction")

    # optional typing
    typing_result: list[
        (
            CgmlstResultIndex |
            MlstResultIndex |
            LineageResultIndex |
            SpatyperResultIndex |
            EmmResultIndex 
        )
    ] = Field(..., discriminator="software", alias="typingResult")
    # optional phenotype prediction
    element_type_result: list[
        (VirulenceMethodIndex | AMRMethodIndex | StressMethodIndex | MethodIndex)
    ] = Field(..., alias="elementTypeResult")
    # optional variant info
    snv_variants: list[VariantBase] | None = None
    sv_variants: list[VariantBase] | None = None
    indel_variants: list[VariantBase] | None = None
    # optional alignment info
    reference_genome: ReferenceGenome | None = None
    read_mapping: str | None = None
    genome_annotation: list[IgvAnnotationTrack] | None = None

