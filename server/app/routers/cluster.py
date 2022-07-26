"""Entrypoints for starting clustering jobs."""
from fastapi import APIRouter, Query, Security, status
from pydantic import constr
from ..crud.user import get_current_active_user
from ..models.user import UserOutputDatabase

router = APIRouter()

DEFAULT_TAGS = [
    "cluster",
]
READ_PERMISSION = "cluster:read"
WRITE_PERMISSION = "cluster:write"

#    current_user: UserOutputDatabase = Security(
#        get_current_active_user, scopes=[WRITE_PERMISSION]
#    ),
@router.get("/cluster/", status_code=status.HTTP_201_CREATED, tags=DEFAULT_TAGS)
async def cluster_samples(
    id: list[str] = Query(default=...),
):
    """Return root message."""
    return {
        "message": "Welcome to the Mimer api",
        "idx": ",".join(id),
    }
