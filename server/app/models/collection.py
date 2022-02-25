"""Routes related to collections of samples."""
from pydantic import BaseModel, Field, FileUrl
from typing import List, Dict
from .base import DBModelMixin, RWModel


class Image(BaseModel):
    url: FileUrl
    name: str


FilterParams = List[
    Dict[str, str | int | float],
]


class CollectionBase(RWModel):
    """Basic specie information."""

    collection_id: str = Field(..., alias="collectionId")
    display_name: str = Field(..., alias="displayName")
    image: Image | None = Field(None)
    filter_params: FilterParams = Field(..., alias="filterParams")


class OverviewTableColumn(BaseModel):
    """Definition of how to display and function of overview table."""

    hidden: bool = Field(False)
    type: str
    name: str
    label: str
    sortable: bool = Field(False)
    filterable: bool = Field(False)
    filter_type: str | None = Field(None, alias="filterType")
    filter_param: str | None = Field(None, alias="filterParam")


class CollectionInCreate(CollectionBase):
    table_columns: List[OverviewTableColumn] = Field(..., alias="tableColumns")


class CollectionInfoDatabase(DBModelMixin, CollectionInCreate):
    pass


class CollectionInfoOut(CollectionBase):
    pass
