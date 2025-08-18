"""Datamodels used for prediction results."""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self

from bonsai_models.base import ApiModel
from bonsai_models.constants import SampleQcStatus
from bonsai_models.schema.qc import VariantRejectionReason
from .constants import (AnnotationType, ElementAmrSubtype,
                       ElementSerotypeSubtype, ElementStressSubtype,
                       ElementType, ElementVirulenceSubtype,
                       PredictionSoftware, SequenceStand, VariantSubType,
                       VariantType)


class PhenotypeInfo(ApiModel):
    """Phenotype information."""

    name: str
    group: str | None = Field(None, description="Name of the group a trait belongs to.")
    type: ElementType = Field(
        ..., description="Trait category, for example AMR, STRESS etc."
    )
    # annotation of the expected resistance level
    resistance_level: str | None = None
    # how was the annotation made
    annotation_type: AnnotationType = Field(..., description="Annotation type")
    annotation_author: str | None = Field(None, description="Annotation author")
    # what information substansiate the annotation
    reference: list[str] = Field([], description="References supporting trait")
    note: str | None = Field(None, description="Note, can be used for confidence score")
    source: str | None = Field(None, description="Source of variant")


class DatabaseReference(ApiModel):
    """Reference to a database."""

    ref_database: str | None = None
    ref_id: str | None = None


class GeneBase(BaseModel):
    """Container for gene information"""

    # basic info
    gene_symbol: str | None = None
    accession: str | None = None
    sequence_name: str | None = Field(
        default=None, description="Reference sequence name"
    )
    element_type: ElementType = Field(
        description="The predominant function of the gene."
    )
    element_subtype: (
        ElementStressSubtype
        | ElementAmrSubtype
        | ElementVirulenceSubtype
        | ElementSerotypeSubtype
    ) = Field(description="Further functional categorization of the genes.")
    # position
    ref_start_pos: int | None = Field(None, description="Alignment start in reference")
    ref_end_pos: int | None = Field(None, description="Alignment end in reference")
    ref_gene_length: int | None = Field(
        default=None,
        alias="target_length",
        description="The length of the reference protein or gene.",
    )

    # prediction
    method: str | None = Field(None, description="Method used to predict gene")
    identity: float | None = Field(None, description="Identity to reference sequence")
    coverage: float | None = Field(None, description="Ratio reference sequence covered")


class AmrFinderGene(GeneBase):
    """Container for Resfinder gene prediction information"""

    contig_id: str
    query_start_pos: int | None = Field(None, description="Start position on the assembly"
    )
    query_end_pos: int | None = Field(None, description="End position on the assembly")
    strand: SequenceStand


class AmrFinderVirulenceGene(AmrFinderGene):
    """Container for a virulence gene for AMRfinder."""


class AmrFinderResistanceGene(AmrFinderGene):
    """AMRfinder resistance gene information."""

    phenotypes: list[PhenotypeInfo] = []


class ResistanceGene(GeneBase):
    """Container for resistance gene information"""

    phenotypes: list[PhenotypeInfo] = []


class SerotypeGene(GeneBase):
    """Container for serotype gene information"""


class VirulenceGene(GeneBase, DatabaseReference):
    """Container for virulence gene information"""

    depth: float | None = Field(
        None, description="Amount of sequence data supporting the gene."
    )


class ResfinderGene(ResistanceGene):
    """Container for Resfinder gene prediction information"""

    depth: float | None = Field(
        None, description="Amount of sequence data supporting the gene."
    )


class VariantBase(ApiModel):
    """Container for mutation information"""

    # classification
    id: int
    variant_type: VariantType
    variant_subtype: VariantSubType
    phenotypes: list[PhenotypeInfo] = []

    # variant location
    reference_sequence: str | None = Field(
        ...,
        description="Reference sequence such as chromosome, gene or contig id.",
        alias="gene_symbol",
    )
    accession: str | None = None
    start: int
    end: int
    ref_nt: str | None = None
    alt_nt: str | None = None
    ref_aa: str | None = None
    alt_aa: str | None = None

    # prediction info
    depth: float | None = Field(None, description="Total depth, ref + alt.")
    frequency: float | None = Field(None, description="Alt allele frequency.")
    confidence: float | None = Field(None, description="Genotype confidence.")
    method: str | None = Field(
        ..., description="Prediction method used to call variant"
    )
    passed_qc: bool | None = Field(
        ..., description="Describe if variant has passed the tool qc check"
    )
    verified: SampleQcStatus = SampleQcStatus.UNPROCESSED
    reason: VariantRejectionReason | None = None

    @model_validator(mode="after")
    def check_assigned_ref_alt(self) -> Self:
        """Check that either ref/alt nt or aa was assigned."""
        unassigned_nt = self.ref_nt is None and self.alt_nt is None
        unassigned_aa = self.ref_aa is None and self.alt_aa is None
        if unassigned_nt and unassigned_aa:
            raise ValueError("Either ref and alt NT or AA must be assigned.")
        return self


class ResfinderVariant(VariantBase):
    """Container for ResFinder variant information"""


class MykrobeVariant(VariantBase):
    """Container for Mykrobe variant information"""


class AmrFinderVariant(VariantBase):
    """Container for AmrFinder variant information."""

    contig_id: str
    query_start_pos: int = Field(..., description="Alignment start in contig")
    query_end_pos: int = Field(..., description="Alignment start in contig")
    ref_gene_length: int | None = Field(
        default=None,
        alias="target_length",
        description="The length of the reference protein or gene.",
    )
    strand: SequenceStand
    coverage: float
    identity: float


class TbProfilerVariant(VariantBase):
    """Container for TbProfiler variant information"""

    variant_effect: str | None = None
    hgvs_nt_change: str | None = Field(..., description="DNA change in HGVS format")
    hgvs_aa_change: str | None = Field(..., description="Protein change in HGVS format")


class VirulenceElementTypeResult(BaseModel):
    """Phenotype result data model.

    A phenotype result is a generic data structure that stores predicted genes,
    mutations and phenotyp changes.
    """

    phenotypes: dict[str, list[str]]
    genes: list[AmrFinderVirulenceGene | VirulenceGene]
    variants: list[Any] = []


class ElementTypeResult(BaseModel):
    """Phenotype result data model.

    A phenotype result is a generic data structure that stores predicted genes,
    mutations and phenotyp changes.
    """

    phenotypes: dict[str, list[str]] = {}
    genes: list[AmrFinderGene | AmrFinderResistanceGene | ResfinderGene]
    variants: list[
        TbProfilerVariant | MykrobeVariant | ResfinderVariant | AmrFinderVariant
    ] = []


class AMRMethodIndex(ApiModel):
    """Container for key-value lookup of analytical results."""

    type: Literal[ElementType.AMR]
    software: PredictionSoftware
    result: ElementTypeResult


class AntigenMethodIndex(ApiModel):
    """Container for key-value lookup of analytical results."""

    type: Literal[ElementType.ANTIGEN]
    software: PredictionSoftware
    result: ElementTypeResult


class StressMethodIndex(ApiModel):
    """Container for key-value lookup of analytical results."""

    type: Literal[ElementType.STRESS]
    software: PredictionSoftware
    result: ElementTypeResult


class VirulenceMethodIndex(ApiModel):
    """Container for key-value lookup of analytical results."""

    type: Literal[ElementType.VIR]
    software: PredictionSoftware
    result: VirulenceElementTypeResult
