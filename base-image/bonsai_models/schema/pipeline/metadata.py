"""Metadata from the pipeline."""

from datetime import datetime
from pydantic import BaseModel
from bonsai_models.base import ApiModel

from .constants import SoupType


class SoupVersion(BaseModel):
    """Version of Software of Unknown Provenance."""

    name: str
    version: str
    type: SoupType


class SequencingInfo(ApiModel):
    """Information on the sample was sequenced."""

    run_id: str
    platform: str
    instrument: str | None = None
    method: dict[str, str] = {}
    date: datetime | None = None


class PipelineInfo(ApiModel):
    """Information on the sample was analysed."""

    pipeline: str
    version: str
    commit: str
    analysis_profile: list[str]
    assay: str
    release_life_cycle: str
    configuration_files: list[str]
    workflow_name: str
    command: str
    softwares: list[SoupVersion]
    date: datetime
