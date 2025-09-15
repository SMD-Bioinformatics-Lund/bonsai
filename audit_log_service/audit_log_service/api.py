"""API entrypoints"""

from http import HTTPStatus
from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from pymongo.errors import PyMongoError

from .core.config import get_settings, Settings
from .audit_repository import AuditTrailRepository
from .db import get_collection
from .version import __version__ as version
from .models import Event

router = APIRouter()

def get_repo(settings: Settings = Depends(get_settings)) -> AuditTrailRepository:
    """Get data repository."""
    col = get_collection(settings)
    return AuditTrailRepository(col)


@router.get("/")
def root() -> dict[str, str]:
    """Display service info."""

    return {"message": "Welcome to Audit Log Service", "version": version}


@router.post("/events", tags=["events"], status_code=HTTPStatus.ACCEPTED)
def post_event(payload: Event, repo: AuditTrailRepository = Depends(get_repo)) -> dict[str, str]:
    """Record a new event."""
    try:
        inserted_id = repo.log_event(payload)
    except PyMongoError as exc:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, 
            detail="A error prevented a event being logged"
        ) from exc
    return {"id": str(inserted_id)}


@router.post("/events:batch", tags=["events"], status_code=HTTPStatus.ACCEPTED)
def post_event_batch(payload: list[Event], repo: AuditTrailRepository = Depends(get_repo)) -> dict[str, list[str]]:
    """Record multiple events."""
    ids: list[str] = []
    try:
        for event in payload:
            inserted_id = str(repo.log_event(event))
            ids.append(inserted_id)
    except PyMongoError as exc:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, 
            detail="A error prevented a event being logged"
        ) from exc
    return {"ids": ids}


@router.get("/system/health", tags=["health"])
def check_health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/system/readiness", tags=["health"])
def readyz(repo: AuditTrailRepository = Depends(get_repo)) -> dict[str, str]:
    """Readiness probe."""
    try:
        repo.check_connection()
    except PyMongoError:
        raise HTTPException(
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            detail="MongoDB is not ready"
        )
    return {"status": "ready"}
