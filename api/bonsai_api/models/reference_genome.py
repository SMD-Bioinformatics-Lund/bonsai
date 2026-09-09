from pydantic import Field, BaseModel

from .base import CreatedAtModelMixin, RWModel, UUIDMixin
from .genomic_resource import ResourceInput, ResourceOutput


class ReferenceGenomeCreate(RWModel):
    """Reference genome definition for creating new reference genomes."""

    name: str = Field(..., description="Human-readable name")
    accession: str = Field(..., description="RefSeq assembly accession, e.g. GCF_000012045.1")
    organism: str = Field(..., description="Scientific name")

    sequence_accessions: list[str] = Field(
        default_factory=list,
        description=(
            "Sequence (chromosome/plasmid) accessions contained in the FASTA, "
            "e.g. ['NC_002951.2']. These are the sequence names IGV uses to "
            "build loci; the first entry is treated as the primary sequence."
        ),
    )

    fasta_resource: str = Field(..., description="Path or URL to FASTA file")
    fasta_index_resource: str = Field(..., description="Path or URL to FASTA index.")

    reference_tracks: list[ResourceInput] = Field(default_factory=list, description="Optional list of reference tracks")


class ReferenceGenomeDb(ReferenceGenomeCreate, CreatedAtModelMixin, UUIDMixin):
    """Canonical reference genome definition."""

class ReferenceGenomeResponse(RWModel):
    """Response model for reference genome."""

    id: str
    name: str = Field(..., description="Human-readable name")
    accession: str = Field(..., description="RefSeq assembly accession, e.g. GCF_000012045.1")
    organism: str = Field(..., description="Scientific name")

    sequence_accessions: list[str] = Field(
        default_factory=list,
        description="Sequence accessions contained in the FASTA; first is primary.",
    )

    fasta_url: str = Field(..., description="Path or URL to FASTA file")
    fasta_index_url: str = Field(..., description="Path or URL to FASTA .fai index")

    reference_tracks: list[ResourceOutput] = Field(default_factory=list, description="Optional list of reference tracks")
    created_at: str


class AddReferenceGenomeRequest(BaseModel):
    """Input for associating a sample with a reference genome."""

    reference_genome_accession: str = Field(
        ..., description="RefSeq assembly accession of the reference genome"
    )
