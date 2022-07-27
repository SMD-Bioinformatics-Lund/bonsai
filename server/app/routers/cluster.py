"""Entrypoints for starting clustering jobs."""
from fastapi import APIRouter, Query, Security, status, HTTPException
from pydantic import constr
from enum import Enum
from ..crud.user import get_current_active_user
from ..crud.sample import get_typing_profiles, TypingProfileOutput
from ..crud.errors import EntryNotFound
from ..models.user import UserOutputDatabase
from ..db import db
from ..internal.cluster import cluster_on_allele_profile, ClusterMethod, DistanceMethod

router = APIRouter()

DEFAULT_TAGS = [
    "cluster",
]
READ_PERMISSION = "cluster:read"
WRITE_PERMISSION = "cluster:write"

class TypingMethod(Enum):
    MLST = "mlst"
    CGMLST = "cgmlst"

#    current_user: UserOutputDatabase = Security(
#        get_current_active_user, scopes=[WRITE_PERMISSION]
#    ),
@router.get("/cluster/{typing_method}/", status_code=status.HTTP_201_CREATED, tags=DEFAULT_TAGS)
async def cluster_samples(
    typing_method: TypingMethod,
    sid: list[str] = Query(default=...),
    distance: DistanceMethod = Query(...),
    method: ClusterMethod = Query(...)
):
    """Cluster samples on their cgmlst profile.
    
    In order to cluster the samples, all samples need to have a profile and be of the same specie.
    """
    try:
        profiles: TypingProfileOutput = await get_typing_profiles(db, sid, typing_method.value)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
    # sanity check that all samples had the desired typing result in the database
    newick_tree: str = cluster_on_allele_profile(profiles, method, distance)
    return newick_tree 