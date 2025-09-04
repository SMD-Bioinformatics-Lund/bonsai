"""Data models and types."""

from enum import StrEnum

from pydantic import BaseModel

Signatures = list[dict[str, int | list[int]]]
SignatureEntry = dict[str, str | Signatures]
SignatureFile = list[SignatureEntry]


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


SimilarSignatures = list[SimilarSignature]
