"""Data model definition of input/ output data"""

import datetime
from pydantic import Field

from bonsai_models.db.sample import CommentInDb, SampleInDb
from bonsai_models.utils.timestamp import get_timestamp
from bonsai_models.base import MultipleRecordsResponseModel

from .pipeline.base import PipelineResult
from .pipeline.species import SpeciesPrediction


class SampleSummary(PipelineResult):
    """Summary of a sample stored in the database."""

    id: str | None = None
    major_specie: SpeciesPrediction

    created_at: datetime.datetime = Field(default_factory=get_timestamp)


class MultipleSampleRecordsResponseModel(MultipleRecordsResponseModel[SampleInDb]):
    """
    Response model for returning multiple SampleInDb records.

    Inherits from:
        MultipleRecordsResponseModel[SampleInDb]: A generic response model for multiple records.
    """
    data: list[SampleInDb] = []


class SampleResponse(SampleInDb):
    """Sample response model"""


class CommentResponse(CommentInDb):
    """Comment response model"""
