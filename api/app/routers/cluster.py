"""Entrypoints for starting clustering jobs."""
import logging
from enum import Enum
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from pydantic import Field

from ..crud.errors import EntryNotFound
from ..crud.sample import (TypingProfileOutput, get_signature_path_for_samples,
                           get_typing_profiles)
from ..db import db
from ..models.base import RWModel
from ..redis import ClusterMethod, DistanceMethod, MsTreeMethods, TypingMethod
from ..redis.allele_cluster import \
    schedule_cluster_samples as schedule_allele_cluster_samples
from ..redis.minhash import schedule_add_genome_signature_to_index
from ..redis.minhash import \
    schedule_cluster_samples as schedule_minhash_cluster_samples

LOG = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_TAGS = [
    "cluster",
]
READ_PERMISSION = "cluster:read"
WRITE_PERMISSION = "cluster:write"


class clusterInput(RWModel):
    sample_ids: list[str] = Field(..., min_length=2, alias="sampleIds")
    distance: DistanceMethod | None = None
    method: ClusterMethod | MsTreeMethods

    class Config:
        use_enum_values = False


#    current_user: UserOutputDatabase = Security(
#        get_current_active_user, scopes=[WRITE_PERMISSION]
#    ),
@router.post(
    "/cluster/{typing_method}/",
    status_code=status.HTTP_201_CREATED,
    tags=["minhash", *DEFAULT_TAGS],
)
async def cluster_samples(
    typing_method: TypingMethod,
    clusterInput: clusterInput,
):
    """Cluster samples on their cgmlst profile.

    In order to cluster the samples, all samples need to have a profile and be of the same specie.
    """
    if typing_method == TypingMethod.MINHASH:
        job = schedule_minhash_cluster_samples(
            clusterInput.sample_ids, clusterInput.method
        )
    else:
        try:
            profiles: TypingProfileOutput = await get_typing_profiles(
                db, clusterInput.sample_ids, typing_method.value
            )
        except EntryNotFound as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(error),
            )
        job = schedule_allele_cluster_samples(profiles, clusterInput.method)
    return job


class indexInput(RWModel):
    sample_ids: list[str] = Field(..., min_length=1)
    force: bool = False


@router.post("/minhash/index", status_code=status.HTTP_202_ACCEPTED, tags=["minhash"])
async def index_genome_signatures(index_input: indexInput):
    """Entrypoint for scheduling indexing of sourmash signatures."""
    try:
        signatures = await get_signature_path_for_samples(db, index_input.sample_ids)
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error)
        )

    # verify results
    if len(signatures) == 0:
        sids = ", ".join(index_input.sample_ids)
        msg = f"No signatures found for samples: {sids}"
        LOG.warning(msg)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=msg,
        )
    signature_paths = [Path(sig["genome_signature"]) for sig in signatures]
    job_id: str = schedule_add_genome_signature_to_index(signature_paths)
    return {"job_id": job_id}
