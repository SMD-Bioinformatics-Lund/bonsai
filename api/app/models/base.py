"""Generic database objects of which several other models are based on."""
from datetime import datetime, timezone

from bson import ObjectId
from pydantic import ConfigDict, BaseModel, Field


class RWModel(BaseModel):  # pylint: disable=too-few-public-methods
    """Base model for read/ write operations"""

    model_config = ConfigDict(
        allow_population_by_alias = True,
        populate_by_name = True,
        use_enum_values = True,
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


class PyObjectId(ObjectId):
    """Class for handeling mongo object ids"""

    @classmethod
    def __get_validators__(cls):
        """Validators"""
        yield cls.validate

    @classmethod
    def validate(cls, v):
        """Validate object id"""
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid object id")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")
