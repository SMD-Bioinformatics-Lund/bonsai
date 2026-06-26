from pydantic import Field, BaseModel

from .base import CreatedAtModelMixin, RWModel, UUIDMixin
from .genomic_resource import ResourceInput, ResourceOutput


class ReferenceGenomeCreate(RWModel):
    """Reference genome definition for creating new reference genomes."""

    name: str = Field(..., description="Human-readable name")
    accession: str = Field(..., description="RefSeq accession")
    organism: str = Field(..., description="Scientific name")

    fasta_resource: str = Field(..., description="Path or URL to FASTA file")
    fasta_index_resource: str = Field(..., description="Path or URL to FASTA index.")

    reference_tracks: list[ResourceInput] = Field(default_factory=list, description="Optional list of reference tracks")


class ReferenceGenomeDb(ReferenceGenomeCreate, CreatedAtModelMixin, UUIDMixin):
    """Canonical reference genome definition."""

class ReferenceGenomeResponse(RWModel):
    """Response model for reference genome."""

    id: str
    name: str = Field(..., description="Human-readable name")
    accession: str = Field(..., description="INSDC/RefSeq accession")
    organism: str = Field(..., description="Scientific name")

    fasta_url: str = Field(..., description="Path or URL to FASTA file")
    fasta_index_url: str = Field(..., description="Path or URL to FASTA .fai index")

    reference_tracks: list[ResourceOutput] = Field(default_factory=list, description="Optional list of reference tracks")
    created_at: str


class AddReferenceGenomeRequest(BaseModel):
    """Inut for adding a reference gnome."""

    reference_genome_id: str
