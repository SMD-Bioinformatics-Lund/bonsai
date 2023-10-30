"""Entrypoints for starting clustering jobs."""
from enum import Enum
import logging

from fastapi import APIRouter, Body, HTTPException, Query, Security, status
from pydantic import Field, constr
from pathlib import Path

from ..crud.errors import EntryNotFound
from ..crud.sample import TypingProfileOutput, get_typing_profiles, get_signature_path_for_samples
from ..crud.minhash import schedule_add_genome_signature_to_index, schedule_cluster_samples
from ..crud.user import get_current_active_user
from ..db import db
from ..internal.cluster import (ClusterMethod,  # cluster_on_allele_profile,
                                DistanceMethod,
                                cluster_on_allele_profile_grapetree_mstrees)
from ..models.base import RWModel
from ..models.user import UserOutputDatabase
from ..redis import check_redis_job_status, JobStatus

LOG = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_TAGS = [
    "cluster",
]
READ_PERMISSION = "cluster:read"
WRITE_PERMISSION = "cluster:write"


class TypingMethod(Enum):
    MLST = "mlst"
    CGMLST = "cgmlst"
    MINHASH = "minhash"


class clusterInput(RWModel):
    sample_ids: list[str] = Field(..., min_length=2, alias="sampleIds")
    distance: DistanceMethod
    method: ClusterMethod

    class Config:
        use_enum_values = False


#    current_user: UserOutputDatabase = Security(
#        get_current_active_user, scopes=[WRITE_PERMISSION]
#    ),
@router.post(
    "/cluster/{typing_method}/", status_code=status.HTTP_201_CREATED, tags=["minhash", *DEFAULT_TAGS]
)
async def cluster_samples(
    typing_method: TypingMethod,
    clusterInput: clusterInput,
):
    """Cluster samples on their cgmlst profile.

    In order to cluster the samples, all samples need to have a profile and be of the same specie.
    """
    if typing_method == TypingMethod.MINHASH:
        job = schedule_cluster_samples(clusterInput.sample_ids, clusterInput.method)
        return job
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
        newick_tree: str = cluster_on_allele_profile_grapetree_mstrees(profiles)
        # sanity check that all samples had the desired typing result in the database
        # newick_tree: str = cluster_on_allele_profile(
        #     profiles, clusterInput.method, clusterInput.distance
        # )

    return newick_tree


class indexInput(RWModel):
    sample_ids: list[str] = Field(..., min_length=1)
    force: bool = False


@router.post("/minhash/index", status_code=status.HTTP_202_ACCEPTED, tags=["minhash"])
async def index_genome_signatures(index_input: indexInput):
    """Entrypoint for scheduling indexing of sourmash signatures."""
    try:
        signatures = await get_signature_path_for_samples(db, index_input.sample_ids)
    except Exception as error:
        LOG.error(error)
        raise error

    # verify results
    if len(signatures) == 0:
        sids = ", ".join(index_input.sample_ids)
        msg = f"No signatures found for samples: {sids}"
        LOG.warning(msg)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=msg,
        )
    signature_paths = [Path(sig['genome_signature']) for sig in signatures]
    job_id: str = schedule_add_genome_signature_to_index(signature_paths)
    return {"job_id": job_id}


@router.get("/minhash/status/{job_id}", status_code=status.HTTP_200_OK, tags=["minhash"])
async def check_job_status(job_id: str) -> JobStatus:
    """Entrypoint for checking status of running jobs."""
    info = check_redis_job_status(job_id=job_id)
    return info