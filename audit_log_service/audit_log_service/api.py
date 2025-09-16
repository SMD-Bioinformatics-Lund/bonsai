"""API entrypoints"""

from http import HTTPStatus
from fastapi import APIRouter, Depends, Query, Request
from fastapi.exceptions import HTTPException
from pymongo.errors import PyMongoError
import datetime as dt

from .core.config import get_settings, Settings
from .audit_repository import AuditTrailRepository
from .db import get_collection
from .version import __version__ as version
from .models import Event, EventFilter, PaginatedEvents

router = APIRouter()

def get_repo(request: Request, settings: Settings = Depends(get_settings)) -> AuditTrailRepository:
    """Get data repository."""
    col = get_collection(request, settings)
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


@router.get("/events", tags=["events"], response_model=PaginatedEvents)
def get_events(
    limit: int = Query(50, ge=1, le=500, description="Max number of events to return (1..500)"),
    skip: int = Query(0, ge=0, description="Number of events to skip"),
    severity: list[str] | None = Query(
        None,
        description="Filter by severity. Repeat to match any of multiple severities.",
        examples=[["info", "error"]],
    ),
    source_service: list[str] | None = Query(
        None,
        description="Filter by source service(s). Repeat to match any.",
        examples=[["bonsai_api", "minhash_service"]],
    ),
    occured_after: dt.datetime | None = Query(
        None, description="Return events with occured_at >= this UTC ISO8601"
    ),
    occured_before: dt.datetime | None = Query(
        None, description="Return events with occured_at <= this UTC ISO8601"
    ),
    repo: AuditTrailRepository = Depends(get_repo)):


    filters = EventFilter(
        severities=severity,
        source_services=source_service,
        occured_after=occured_after,
        occured_before=occured_before,
    )

    events = repo.get_events(limit=limit, skip=skip, filters=filters)
    return events


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
