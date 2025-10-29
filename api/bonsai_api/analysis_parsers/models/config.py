"""Sample configuration with paths to output files."""

from pydantic import Field

from prp.models.metadata import MetaEntry

from .base import FilePath, RWModel


class IgvAnnotation(RWModel):
    """Format of a IGV annotation track."""

    name: str
    type: str
    uri: str | None = None
    index_uri: str | None = None


class SampleConfig(RWModel):
    """Sample information with metadata and results files."""

    # Sample information
    sample_id: str = Field(..., alias="sampleId", min_length=3, max_length=100)
    sample_name: str
    lims_id: str

    # Bonsai paramters
    groups: list[str] = []
    metadata: list[MetaEntry] = []

    # Reference genome
    ref_genome_sequence: FilePath  | None = None
    ref_genome_annotation: FilePath  | None = None

    igv_annotations: list[IgvAnnotation] = []

    # Jasen result files
    # nextflow_run_info: FilePath
    nextflow_run_info: FilePath
    software_info: list[FilePath] = []  # store sw and db version info

    ## Classification
    kraken: FilePath | None = None

    ## QC
    quast: FilePath
    postalnqc: FilePath | None = None
    gambitcore: FilePath | None = None
    nanoplot: FilePath | None = None

    ## typing
    mlst: FilePath | None = None
    chewbbaca: FilePath | None = None
    serotypefinder: FilePath | None = None
    shigapass: FilePath | None = None
    emmtyper: FilePath | None = None
    spatyper: FilePath | None = None
    sccmec: FilePath | None = None

    ## resistance, virulence etc
    amrfinder: FilePath | None = None
    resfinder: FilePath | None = None
    virulencefinder: FilePath | None = None
    mykrobe: FilePath | None = None
    tbprofiler: FilePath | None = None

    ## clustering
    sourmash_signature: str | None = None
    ska_index: str | None = None

    def assinged_to_group(self) -> bool:
        """Return True if sample is assigned to a group."""
        return len(self.groups) > 0
