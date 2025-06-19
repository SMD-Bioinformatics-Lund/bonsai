"""Pipeline results."""

from typing import Literal
from pydantic import Field

from bonsai_models.base import RWModel
from bonsai_models.schema.pipeline.constants import TypingMethod, TypingSoftware
from .metadata import PipelineInfo, SequencingInfo
from .phenotype import (AMRMethodIndex, StressMethodIndex, VariantBase,
                       VirulenceMethodIndex)
from .qc import QcMethodIndex
from .species import SppMethodIndex
from .typing_result import (EmmTypingMethodIndex, ResultLineageBase,
                           ShigaTypingMethodIndex, SpatyperTypingMethodIndex,
                           TbProfilerLineage, TypingResultCgMlst,
                           TypingResultGeneAllele, TypingResultMlst)

SCHEMA_VERSION: int = 2


class MethodIndex(RWModel):
    """Container for key-value lookup of analytical results."""

    type: TypingMethod
    software: TypingSoftware | None
    result: (
        TypingResultMlst
        | TypingResultCgMlst
        | TypingResultGeneAllele
        | TbProfilerLineage
        | ResultLineageBase
        | SpatyperTypingMethodIndex
    )


class IgvAnnotationTrack(RWModel):
    """IGV annotation track data."""

    name: str  # track name to display
    file: str  # path to the annotation file


class ReferenceGenome(RWModel):
    """Reference genome."""

    name: str
    accession: str
    fasta: str
    fasta_index: str | None = None
    genes: str


class PipelineResult(RWModel):
    """Input format of sample object from pipeline."""

    sample_id: str = Field(..., alias="sampleId", min_length=3, max_length=100)
    sample_name: str
    lims_id: str

    # metadata
    sequencing: SequencingInfo
    pipeline: PipelineInfo

    # quality
    qc: list[QcMethodIndex] = Field(...)

    # species identification
    species_prediction: list[SppMethodIndex] = Field(..., alias="speciesPrediction")

    schema_version: Literal[2] = SCHEMA_VERSION
    # optional typing
    typing_result: list[
        (
            ShigaTypingMethodIndex
            | EmmTypingMethodIndex
            | SpatyperTypingMethodIndex
            | MethodIndex
        )
    ] = Field(..., alias="typingResult")
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
