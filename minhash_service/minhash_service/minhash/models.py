"""Data models and types."""

from pathlib import Path
from pydantic import BaseModel, ConfigDict
from datetime import datetime


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


SimilarSignatures = list[SimilarSignature]

class SignatureInDB(BaseModel):
    """Signature in database"""

    sample_id: str
    signature_path: Path
    checksum: str
    has_been_indexed: bool = False
    indexed_at: datetime | None = None
    exclude_from_index: bool = False

    model_config = ConfigDict(
        orm_mode = True,
        allow_population_by_field_name = True,
        use_enum_values = True,
    )
