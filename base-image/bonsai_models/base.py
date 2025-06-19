"""Generic database objects of which several other models are based on."""

from typing import Generic, TypeVar

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


class ApiModel(BaseModel):
    """
    ApiModel serves as the base model for read and write operations, providing common configuration for all derived models.
    It utilizes Pydantic's ConfigDict to:
    - Allow population of fields by their names.
    - Use enum values instead of enum members.
    - Serialize ObjectId instances as strings in JSON output.
    """
    model_config = ConfigDict(
        populate_by_name=True, use_enum_values=True, json_encoders={ObjectId: str}
    )


T = TypeVar("T")


class MultipleRecordsResponseModel(ApiModel, Generic[T]
):
    """Generic response model for multiple data records."""

    data: list[T] = Field(...)
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
