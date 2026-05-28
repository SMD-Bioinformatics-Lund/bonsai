from pydantic import Field

from .base import RWModel, Timestamps


class ReferenceGenomeDb(RWModel, Timestamps):
    """Canonical reference genome definition (global, de-duplicated)."""

    id: str = Field(..., description="Stable internal reference genome ID")
    name: str = Field(..., description="Human-readable name, e.g. GRCh38")
    accession: str = Field(..., description="INSDC/RefSeq accession")
    organism: str = Field(..., description="Scientific name, e.g. Homo sapiens")

    fasta_url: str = Field(..., description="Path or URL to FASTA file")
    fasta_index_url: str = Field(..., description="Path or URL to FASTA .fai index")

    gene_annotation_url: str | None = Field(
        None, description="Optional GTF/GFF gene annotation"
    )

    source: str | None = Field(None, description="e.g. Ensembl, RefSeq")
    version: str | None = Field(None, description="Reference version")
