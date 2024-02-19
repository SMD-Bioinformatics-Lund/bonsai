"""Data model definition of input/ output data"""
from datetime import datetime
from typing import List

from prp.models import PipelineResult
from prp.models.species import SpeciesPrediction
from pydantic import BaseModel, Field

from ..models.tags import Tag
from .base import DBModelMixin, ModifiedAtRWModel
from .qc import QcClassification

CURRENT_SCHEMA_VERSION = 1
SAMPLE_ID_PATTERN = r"^[a-zA-Z0-9-_]+$"


class Comment(BaseModel):  # pylint: disable=too-few-public-methods
    """Contianer for comments."""

    username: str = Field(..., min_length=0)
    created_at: datetime = Field(datetime.now())
    comment: str = Field(..., min_length=0)
    displayed: bool = True


class CommentInDatabase(Comment):  # pylint: disable=too-few-public-methods
    """Comment data structure in database."""

    id: int = Field(..., alias="id")


class SampleBase(ModifiedAtRWModel):  # pylint: disable=too-few-public-methods
    """Base datamodel for sample data structure"""

    patient_id: str | None = Field(None)
    tags: List[Tag] = []
    qc_status: QcClassification = QcClassification()
    # comments and non analytic results
    comments: List[CommentInDatabase] = []
    location: str | None = Field(None, description="Location id")
    # signature file name
    genome_signature: str | None = Field(None, description="Genome signature name")


class SampleInCreate(
    SampleBase, PipelineResult
):  # pylint: disable=too-few-public-methods
    """Sample data model used when creating new db entries."""


class SampleInDatabase(
    DBModelMixin, SampleBase, PipelineResult
):  # pylint: disable=too-few-public-methods
    """Sample database model outputed from the database."""


class SampleSummary(
    DBModelMixin, SampleBase, PipelineResult
):  # pylint: disable=too-few-public-methods
    """Summary of a sample stored in the database."""

    major_specie: SpeciesPrediction = Field(...)