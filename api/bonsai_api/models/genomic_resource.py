from pydantic import Field

from .base import RWModel, UUIDMixin, TimestampsMixin
from .enums import Visibility


class GenomicResourceBase(RWModel):
    """BED file track."""

    # Classification
    format: str = Field(..., description="File format, e.g. bed, gff, gtf")
    type: str = Field(..., description="alignment | variant | annotation")

    # File access
    url: str = Field(..., description="Path or URL to BED file")
    index_url: str | None = Field(
        None, description="Optional path or URL to index file."
    )

    # Metadata
    name: str = Field(..., description="Track name shown in IGV")


class GenomicResourceCreate(RWModel):
    """Genomic analysis artefacts for a sample."""

    reference_genome_id: str
    pipeline_run_id: str | None
    resources: list[GenomicResourceBase] = Field(default_factory=list, description="List of genomic resources")
    visibility: Visibility = Visibility.PRIVATE


class GenomicResourceDb(GenomicResourceBase, UUIDMixin, TimestampsMixin):
    """Genomic analysis artefacts for a sample, suitable for IGV."""

    # Relationships
    pipeline_run_id: str | None = Field(
        None, description="Pipeline run that produced these assets"
    )
    reference_genome_id: str = Field(
        ..., description="Reference genome used for alignment and variant calling"
    )

    # Access control
    visibility: Visibility


class GenomicResourceOut(GenomicResourceDb):
    """Genomic resource returned to clients."""
