"""Lims export models"""

from enum import StrEnum
from pydantic import BaseModel, Field


class DataType(StrEnum):
    """Valid data types."""

    SPECIES = "species"
    MLST = "mlst"
    EMM = "emm"


class FieldDefinition(BaseModel):
    """A data field."""

    parameter_name: str = Field(..., description="What the parameter is going to be callsed", examples=["STREP ART"])
    data_type: DataType = Field(..., description="Name of the function used to extract the info")


class AssayConfig(BaseModel):
    """Defines export format configuration."""

    assay: str
    fields: list[FieldDefinition]


ExportConfiguration = list[AssayConfig]


class LimsRsResult(BaseModel):
    """A LIMS-RS result which represent a row in a csv file."""

    sample_id: str
    parameter_name: str
    parameter_value: str
    comment: str = ""
