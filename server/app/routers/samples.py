from fastapi import APIRouter, Query, Path, status
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, List, Union

from ..db import db
from ..crud.sample import create_sample as create_sample_record

from ..models.sample import (
    SampleInPipelineInput,
    SampleInDatabase,
    SampleInCreate,
    SAMPLE_ID_PATTERN,
)


samples = {}

router = APIRouter()


@router.get("/samples/", tags=["samples"])
async def read_samples(limit: int = Query(10, gt=0), skip: int = Query(10, gt=-1)):
    return list(samples.values())[:limit]


@router.get("/samples/{sample_id}")
async def read_sample(
    sample_id: str = Path(
        ...,
        title="ID of the sample to get",
        min_length=3,
        max_length=100,
        regex=SAMPLE_ID_PATTERN,
    )
):
    # return samples.get(sample_id)
    return {"sample_id": sample_id}


@router.post("/samples/", status_code=status.HTTP_201_CREATED)
async def create_sample(sample: SampleInPipelineInput):
    db_obj = await create_sample_record(db, sample)
    return db_obj
