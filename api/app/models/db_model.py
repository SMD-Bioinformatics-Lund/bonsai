"""Generic database objects of which several other models are based on."""
from datetime import datetime

from pydantic import BaseModel, Field


class DateTimeModelMixin(BaseModel):
    """Add explicit time stamps to database model."""

    created_at: datetime | None = Field(None, alias="createdAd")
    modified_at: datetime | None = Field(None, alias="modifiedAt")


class DBModelMixin(DateTimeModelMixin):
    id: str | None = Field(None)
