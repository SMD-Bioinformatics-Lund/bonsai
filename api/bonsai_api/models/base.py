"""Generic database objects of which several other models are based on."""

import datetime
from typing import Any

from bson import ObjectId as BaseObjectId
from pydantic import BaseModel, ConfigDict, Field, computed_field

from ..utils import get_timestamp


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

    created_at: datetime.datetime = Field(default_factory=get_timestamp)


class DBModelMixin(DateTimeModelMixin):  # pylint: disable=too-few-public-methods
    """Default database model."""

    id: str | None = Field(None)


class ModifiedAtRWModel(RWModel):  # pylint: disable=too-few-public-methods
    """Base RW model that keep reocrds of when a document was last modified."""

    created_at: datetime.datetime = Field(default_factory=get_timestamp)
    modified_at: datetime.datetime = Field(default_factory=get_timestamp)


class MultipleRecordsResponseModel(RWModel):  # pylint: disable=too-few-public-methods
    """Generic response model for multiple data records."""

    data: list[dict[str, Any]] = Field(...)
    records_total: int = Field(
        ...,
        alias="recordsTotal",
        description="Number of db records matching the query",
    )

    @computed_field(alias="recordsFiltered")
    @property
    def records_filtered(self) -> int:
        """
        Number of db returned records after narrowing the result.

        The result can be reduced with limit and skip operations etc.
        """
        return len(self.data)
