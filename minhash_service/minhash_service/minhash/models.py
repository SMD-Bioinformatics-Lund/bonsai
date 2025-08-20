"""Data models and types."""

from enum import StrEnum

from pydantic import BaseModel

Signatures = list[dict[str, int | list[int]]]
SignatureEntry = dict[str, str | Signatures]
SignatureFile = list[SignatureEntry]


class SignatureName(BaseModel):
    """Signature name"""

    name: str
    filename: str


class SimilarSignature(BaseModel):  # pydantic: disable=too-few-public-methods
    """Container for similar signature result"""

    sample_id: str
    similarity: float


class IndexFormat(StrEnum):
    """Valid data formats for sourmash indexes"""

    SBT = "SBT"
    ZIP = "zip"
    ROCKSDB = "rocksdb"


SimilarSignatures = list[SimilarSignature]
