"""Resources shared by many routers."""

from fastapi import Path

from ..models.sample import SAMPLE_ID_PATTERN

SAMPLE_ID_PATH: str = Path(
    ...,
    title="ID of the sample to get",
    min_length=3,
    max_length=100,
    pattern=SAMPLE_ID_PATTERN,
)
