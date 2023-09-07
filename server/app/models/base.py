"""Generic database objects of which several other models are based on."""
from datetime import datetime

from bson import ObjectId
from pydantic import BaseConfig, BaseModel, Field


class DateTimeModelMixin(BaseModel):
    """Add explicit time stamps to database model."""

    created_at: datetime | None = Field(None)


class DBModelMixin(DateTimeModelMixin):
    id: str | None = Field(None)


class RWModel(BaseModel):
    """Base model for read/ write operations"""

    class Config(BaseConfig):
        allow_population_by_alias = True
        populate_by_name = True
        use_enum_values = True


class ModifiedAtRWModel(RWModel):
    """Base RW model that keep reocrds of when a document was last modified."""

    created_at: datetime = Field(datetime.utcnow())
    modified_at: datetime = Field(datetime.utcnow())


class PyObjectId(ObjectId):
    """Class for handeling mongo object ids"""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid object id")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")
