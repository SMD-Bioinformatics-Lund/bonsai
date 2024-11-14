"""Generic database objects of which several other models are based on."""

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId as BaseObjectId
from pydantic import BaseModel, ConfigDict, Field, computed_field


class ObjectId(BaseObjectId):
    """Class for handeling mongo object ids"""

    @classmethod
    def __get_validators__(cls):
        """Validators"""
        yield cls.validate

    @classmethod
    def validate(cls, v):
        """Validate object id"""
        if not BaseObjectId.is_valid(v):
            raise ValueError("Invalid object id")
        return BaseObjectId(v)


class RWModel(BaseModel):  # pylint: disable=too-few-public-methods
    """Base model for read/ write operations"""

    model_config = ConfigDict(
        allow_population_by_alias=True,
        populate_by_name=True,
        use_enum_values=True,
    )


class DateTimeModelMixin(BaseModel):  # pylint: disable=too-few-public-methods
    """Add explicit time stamps to database model."""

    created_at: datetime | None = Field(None)


class DBModelMixin(DateTimeModelMixin):  # pylint: disable=too-few-public-methods
    """Default database model."""

    id: str | None = Field(None)


class ModifiedAtRWModel(RWModel):  # pylint: disable=too-few-public-methods
    """Base RW model that keep reocrds of when a document was last modified."""

    created_at: datetime = Field(datetime.now(timezone.utc))
    modified_at: datetime = Field(datetime.now(timezone.utc))


class MultipleRecordsResponseModel(RWModel):  # pylint: disable=too-few-public-methods
    """Generic response model for multiple data records."""

    data: list[dict[str, Any]] = Field(...)
    records_total: int = Field(..., alias="recordsTotal")

    @computed_field(alias="recordsFiltered")
    def records_filtered(self) -> int:
        return len(self.data)
