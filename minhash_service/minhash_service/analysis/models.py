"""Data models and types."""

from enum import StrEnum

from pydantic import BaseModel, Field

Signatures = list[dict[str, int | list[int]]]
SignatureEntry = dict[str, str | Signatures]
SignatureFile = list[SignatureEntry]


class ClusterMethod(StrEnum):
    """Index of methods for hierarchical clustering of samples."""

    SINGLE = "single"
    COMPLETE = "complete"
    AVERAGE = "average"


class AniEstimateOptions(StrEnum):
    """What ANI should be estimated from"""

    JACCARD = "jaccard_similarity"
    CONTAINMENT = "containment"
    MAX_CONTAINMENT = "max_containment"
    AVG_CONTAINMENT = "avg_containment"


class SignatureName(BaseModel):
    """Signature name"""

    name: str
    filename: str


class SimilarSignature(BaseModel):  # pydantic: disable=too-few-public-methods
    """Container for similar signature result"""

    sample_id: str
    similarity: float


class SimilaritySearchConfig(BaseModel):
    """Parameters for similarity searches."""

    min_similarity: float = Field(
        ge=0,
        le=1,
        description="Only inlcude samples with a similarity score equal or greater than threshold.",
    )
    ani_estimate: AniEstimateOptions = Field(
        default=AniEstimateOptions.JACCARD,
        description="How sourmash should estimate average nucleotide identity (ANI).",
    )
    limit: int | None = Field(
        default=None, description="Limit the search results to N hits."
    )
    ignore_abundance: bool = Field(
        default=False,
        description="If abundance information in Sourmash signature be ignored.",
    )
    subset_checksums: list[str] | None = Field(
        default=None, description="Subset search to signatures with checksum."
    )


SimilarSignatures = list[SimilarSignature]
