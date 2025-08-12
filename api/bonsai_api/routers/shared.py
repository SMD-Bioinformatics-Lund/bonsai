"""Resources shared by many routers."""

from enum import StrEnum

from bonsai_models.models.sample import SAMPLE_ID_PATTERN
from fastapi import Path

SAMPLE_ID_PATH: str = Path(
    ...,
    title="ID of the sample to get",
    min_length=3,
    max_length=100,
    pattern=SAMPLE_ID_PATTERN,
)


class RouterTags(StrEnum):

    AUTH = "authentication"
    SAMPLE = "sample"
    GROUP = "group"
    META = "metadata"
    USR = "user"
    EXP = "export"
    JOB = "job"
    ASSET = "resources"
    CLS = "cluster"
    LOC = "location"
