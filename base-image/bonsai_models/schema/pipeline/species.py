"""Species related data models."""

from pydantic import Field
from bonsai_models.base import RWModel

from .constants import SppPredictionSoftware, TaxLevel


class SpeciesPrediction(RWModel):
    """Species prediction results."""

    scientific_name: str = Field(..., alias="scientificName")
    taxonomy_id: int | None = Field(..., alias="taxId")


class BrackenSpeciesPrediction(SpeciesPrediction):
    """Species prediction results."""

    taxonomy_lvl: TaxLevel = Field(..., alias="taxLevel")
    kraken_assigned_reads: int = Field(..., alias="krakenAssignedReads")
    added_reads: int = Field(..., alias="addedReads")
    fraction_total_reads: float = Field(..., alias="fractionTotalReads")


class MykrobeSpeciesPrediction(SpeciesPrediction):
    """Mykrobe species prediction results."""

    phylogenetic_group: str = Field(
        ..., description="Group with phylogenetic related species."
    )
    phylogenetic_group_coverage: float = Field(
        ..., description="Kmer converage for phylo group."
    )
    species_coverage: float = Field(..., description="Species kmer converage.")


class SppMethodIndex(RWModel):
    """Container for key-value lookup of analytical results."""

    software: SppPredictionSoftware
    result: list[BrackenSpeciesPrediction | MykrobeSpeciesPrediction]
