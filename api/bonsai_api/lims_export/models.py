"""Lims export models"""

from enum import StrEnum
from typing import Any, Literal, Mapping, Protocol

from bonsai_api.models.sample import SampleInDatabase
from pydantic import BaseModel, ConfigDict, Field

LimsAtomic = str | int | float | Literal["novel"]
LimsValue = LimsAtomic | None  # None = missing/unavailable
LimsComment = str | None


class DataType(StrEnum):
    """Valid data types."""

    SPECIES = "species"
    QC = "qc"
    MLST = "mlst"
    EMM = "emm"
    LINEAGE = "lineage"
    AMR = "amr"


class FieldDefinition(BaseModel):
    """A data field."""

    model_config = ConfigDict(populate_by_name=True)

    parameter_name: str = Field(
        ...,
        description="What the parameter is going to be callsed",
        examples=["STREP ART"],
    )
    data_type: DataType = Field(
        ..., description="Name of the function used to extract the info"
    )
    required: bool = Field(..., description="If True, Will consider missing as errors.")
    options: dict[str, Any] = Field(
        default={}, description="Optional arguments to be passed to formatter function."
    )


class AssayConfig(BaseModel):
    """Defines export format configuration."""

    assay: str
    fields: list[FieldDefinition]


ExportConfiguration = list[AssayConfig]


class LimsRsResult(BaseModel):
    """A LIMS-RS result which represent a row in a csv file."""

    sample_name: str
    parameter_name: str
    parameter_value: LimsValue
    comment: str = ""


class Formatter(Protocol):
    def __call__(
        self, sample: SampleInDatabase, *, options: Mapping[str, Any] | None = None
    ) -> tuple[LimsValue, str]: ...
