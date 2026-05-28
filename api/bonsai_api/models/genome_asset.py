from pydantic import Field

from .base import RWModel
from .enums import Visibility


class BedTrack(RWModel):
    """BED file track."""

    name: str = Field(..., description="Track name shown in IGV")
    url: str = Field(..., description="Path or URL to BED file")


class GenomicAssetCreate(RWModel):
    """Genomic analysis artefacts for a sample."""

    reference_genome_id: str
    pipeline_run_id: str | None
    bam_url: str
    bam_index_url: str
    vcf_url: str | None
    vcf_index_url: str | None
    bed_files: list[BedTrack] = Field(default_factory=list)
    visibility: Visibility


class GenomicAssetDb(RWModel):
    """Genomic analysis artefacts for a sample, suitable for IGV."""

    id: str

    # Relationships
    sample_id: str = Field(..., description="Owning sample ID")
    pipeline_run_id: str | None = Field(
        None, description="Pipeline run that produced these assets"
    )

    reference_genome_id: str = Field(
        ..., description="Reference genome used for alignment and variant calling"
    )

    # Core files
    bam_url: str = Field(..., description="Aligned reads (BAM)")
    bam_index_url: str = Field(..., description="BAM index (.bai)")

    vcf_url: str | None = Field(
        None, description="Variant calls (bgzipped VCF)"
    )
    vcf_index_url: str | None = Field(
        None, description="VCF index (.tbi)"
    )

    bed_files: list["BedTrack"] = Field(
        default_factory=list,
        description="Optional BED tracks"
    )

    # IGV presentation
    igv_tracks: list["IgvTrackConfig"] | None = None

    # Access control (may inherit from sample)
    visibility: Visibility
    access_groups: list[str] = Field(default_factory=list)


class GenomicAssetOut(GenomicAssetDb):
    pass


class GenomicAssetListResponse(RWModel):
    items: list[GenomicAssetOut]


class IgvTrackConfig(RWModel):
    """IGV.js track configuration."""

    name: str = Field(..., description="Track display name")
    type: str = Field(
        ..., description="alignment | variant | annotation"
    )

    url: str = Field(..., description="Primary data file")
    index_url: str | None = Field(
        None, description="Optional index file (.bai, .tbi)"
    )

    format: str | None = Field(
        None, description="bam | vcf | bed | gff | gtf"
    )

    color: str | None = Field(None, description="Optional IGV colour")
    height: int | None = Field(None, description="Track height in pixels")