"""Metadata models."""
from datetime import datetime
from enum import Enum
from typing import List

from pydantic import BaseModel

from .base import RWModel


class SoupType(Enum):
    """Type of software of unkown provenance."""

    DB = "database"
    SW = "software"


class SequencingPlatform(Enum):
    """Valid sequencing platform names."""

    ILLUMINA = "illumina"
    ION_TORRENT = "ion torrent"
    ONP = "oxford nanopore"
    PACBIO = "pacbio"


class SequencingType(Enum):
    """Sequencing methods."""

    SINGLE_END = "SE"
    PAIRED_END = "PE"


class SoupVersion(RWModel):  # pylint: disable=too-few-public-methods
    """Version of Software of Unknown Provenance."""

    name: str
    version: str
    type: SoupType


class RunInformation(RWModel):  # pylint: disable=too-few-public-methods
    """Store information on a run how the run was conducted."""

    pipeline: str
    version: str
    commit: str
    analysis_profile: str
    configuration_files: List[str]
    workflow_name: str
    sample_name: str
    sequencing_platform: SequencingPlatform
    sequencing_type: SequencingType
    command: str
    date: datetime


SoupVersions = List[SoupVersion]


class RunMetadata(BaseModel):  # pylint: disable=too-few-public-methods
    """Run metadata"""

    run: RunInformation
    databases: SoupVersions
