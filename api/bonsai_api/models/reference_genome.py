from pydantic import Field

from .base import CreatedAtModelMixin, RWModel, UUIDModelMixin


class ReferenceGenomeCreate(RWModel):
    """Reference genome definition for creating new reference genomes."""

    name: str = Field(..., description="Human-readable name")
    accession: str = Field(..., description="RefSeq accession")
    organism: str = Field(..., description="Scientific name")

    fasta_resource: str = Field(..., description="Path or URL to FASTA file")
    fasta_index_resource: str = Field(..., description="Path or URL to FASTA index.")

    genome_annotation_resource: str | None = Field(
        None, description="Optional GTF/GFF gene annotation"
    )


class ReferenceGenomeDb(ReferenceGenomeCreate, CreatedAtModelMixin, UUIDModelMixin):
    """Canonical reference genome definition."""

class ReferenceGenomeResponse(RWModel):
    """Response model for reference genome."""

    id: str
    name: str = Field(..., description="Human-readable name")
    accession: str = Field(..., description="INSDC/RefSeq accession")
    organism: str = Field(..., description="Scientific name")

    fasta_url: str = Field(..., description="Path or URL to FASTA file")
    fasta_index_url: str = Field(..., description="Path or URL to FASTA .fai index")

    genome_annotation_url: str | None = Field(
        None, description="Optional GTF/GFF gene annotation"
    )
    created_at: str
