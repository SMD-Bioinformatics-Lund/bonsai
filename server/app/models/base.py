"""Generic database objects of which several other models are based on."""
from datetime import datetime
from pydantic import BaseModel, Field, BaseConfig


class DateTimeModelMixin(BaseModel):
    """Add explicit time stamps to database model."""

    created_at: datetime | None = Field(None, alias="createdAt")
    modified_at: datetime | None = Field(None, alias="modifiedAt")


class DBModelMixin(DateTimeModelMixin):
    id: str | None = Field(None)


class RWModel(BaseModel):
    class Config(BaseConfig):
        allow_population_by_alias = True
        allow_population_by_field_name = True
        use_enum_values = True
