"""Entrypoints for starting clustering jobs."""
from enum import Enum

from fastapi import APIRouter, Body, HTTPException, Query, Security, status
from pydantic import Field, constr

from ..crud.errors import EntryNotFound
from ..crud.sample import TypingProfileOutput, get_typing_profiles
from ..crud.user import get_current_active_user
from ..db import db
from ..internal.cluster import (ClusterMethod,  # cluster_on_allele_profile,
                                DistanceMethod,
                                cluster_on_allele_profile_grapetree_mstrees,
                                cluster_on_minhash_signature)
from ..models.base import RWModel
from ..models.user import UserOutputDatabase

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
    "/cluster/{typing_method}/", status_code=status.HTTP_201_CREATED, tags=DEFAULT_TAGS
)
async def cluster_samples(
    typing_method: TypingMethod,
    clusterInput: clusterInput,
):
    """Cluster samples on their cgmlst profile.

    In order to cluster the samples, all samples need to have a profile and be of the same specie.
    """
    if typing_method == TypingMethod.MINHASH:
        newick_tree = cluster_on_minhash_signature(
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
        newick_tree: str = cluster_on_allele_profile_grapetree_mstrees(profiles)
        # sanity check that all samples had the desired typing result in the database
        # newick_tree: str = cluster_on_allele_profile(
        #     profiles, clusterInput.method, clusterInput.distance
        # )

    return newick_tree
