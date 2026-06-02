from pydantic import Field

from .base import RWModel, UUIDMixin, TimestampsMixin
from .enums import Visibility


class GenomicResourceBase(RWModel):
    """BED file track."""

    # Classification
    format: str = Field(..., description="File format, e.g. bed, gff, gtf")
    type: str = Field(..., description="alignment | variant | annotation")

    # Metadata
    name: str = Field(..., description="Track name shown in IGV")


class ResourceInput(GenomicResourceBase):
    """Genomic resource input from clients with paths."""

    path: str = Field(..., description="Path to main resource file")
    index_path: str | None = Field(
        None, description="Optional path to index file."
    )


class ResourceOutput(GenomicResourceBase):
    """Genomic resource output for clients, with URLs."""

    url: str = Field(..., description="URL to main resource file")
    index_url: str | None = Field(
        None, description="Optional URL to index file."
    )


class GenomicResourceCreate(RWModel):
    """Genomic analysis artefacts for a sample."""

    reference_genome_id: str
    pipeline_run_id: str | None
    resource_data: list[ResourceInput] = Field(default_factory=list, description="List of genomic resources")
    visibility: Visibility = Visibility.PRIVATE


class GenomicResourceDb(ResourceInput, UUIDMixin):
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


class GenomicResourceResponse(ResourceOutput, UUIDMixin):
    """Genomic resource returned to clients."""

    # Relationships
    pipeline_run_id: str | None = Field(
        None, description="Pipeline run that produced these assets"
    )
    reference_genome_id: str = Field(
        ..., description="Reference genome used for alignment and variant calling"
    )

    # Access control
    visibility: Visibility