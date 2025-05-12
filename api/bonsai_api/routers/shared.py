"""Resources shared by many routers."""

from fastapi import Path
from enum import StrEnum

from bonsai_models.models.sample import SAMPLE_ID_PATTERN

SAMPLE_ID_PATH: str = Path(
    ...,
    title="ID of the sample to get",
    min_length=3,
    max_length=100,
    pattern=SAMPLE_ID_PATTERN,
)

class RouterTags(StrEnum):

    AUTH = 'authentication'
    SAMPLE = 'sample'
    GROUP = 'groups'
    META = 'metadata'
    USR = 'user'