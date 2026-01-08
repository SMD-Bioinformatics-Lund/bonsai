"""Services for ingesting analysis output files."""

import logging
from api_client.audit_log.models import Subject, SourceType
from api_client.audit_log import AuditLogClient, EventCreate
from bonsai_api.crud.analysis import create_analysis
from bonsai_api.crud.sample import sample_exists
from bonsai_api.parsers.registry import get_parser
from bonsai_api.dependencies import ApiRequestContext
from bonsai_api.utils import get_timestamp
from bonsai_api.exceptions import EntryNotFound

LOG = logging.getLogger(__name__)


async def ingest_analysis_service(
    db,
    *,
    sample_id: str,
    analysis_type: str,
    software: str,
    software_version: str | None,
    file,
    ctx: ApiRequestContext | None = None,
    audit: AuditLogClient | None = None,
) -> str:
    """Parse submitted analysis file and persist an analysis record.

    Raises EntryNotFound (via get_sample) if sample not present.
    """
    # ensure sample exists
    if await sample_exists(db, sample_id=sample_id):
        raise EntryNotFound("Sample not found", sample_id=sample_id)

    parser = get_parser(analysis_type, software, software_version)
    parsed = await parser(file)

    doc = {
        "sample_id": sample_id,
        "analysis_type": analysis_type,
        "software": software,
        "software_version": software_version,
        "parsed": parsed,
        "uploaded_at": get_timestamp(),
    }

    # audit event
    if isinstance(audit, AuditLogClient):
        subject = Subject(id=sample_id, type=SourceType.USR)
        event = EventCreate(
            source_service="bonsai_api",
            event_type="ingest_analysis",
            actor=ctx.actor if ctx else None,
            subject=subject,
            metadata={"software": software, "analysis_type": analysis_type},
        )
        audit.post_event(event)

    inserted_id = await create_analysis(db, doc=doc)
    LOG.info("Ingested analysis %s for %s", inserted_id, sample_id)
    return inserted_id
