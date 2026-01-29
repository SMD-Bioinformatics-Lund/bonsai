"""Services for ingesting analysis output files."""

import logging

from fastapi import UploadFile
from pydantic import ValidationError
from bonsai_api.crud.utils import managed_transaction
from bonsai_api.models.analysis import (
    AnalysisResult,
    Envelope,
    ResultStatus,
    PRPParserOutput,
    PrpAnalysisType,
)
from bonsai_api.models.sample import AnalysisViewEntry
from api_client.audit_log.models import Subject, SourceType
from api_client.audit_log import AuditLogClient, EventCreate
from bonsai_api.crud.analysis import analysis_exists, create_analysis
from bonsai_api.crud.sample import sample_exists, upsert_analysis_results
from bonsai_api.dependencies import ApiRequestContext
from bonsai_api.exceptions import (
    AnalysisExistsError,
    EntryNotFound,
    ParserError,
    InvalidDataFormat,
)

from prp.parse import run_parser


LOG = logging.getLogger(__name__)

TYPING_RESULT = "typing_result"
ELEMENT_TYPE_RESULT = "element_type_result"
QC_RESULT = "qc"
SPP_RESULT = "species_prediction"
GROUP_FOR: dict[str, str] = {
    "abst": TYPING_RESULT,
    "amr": ELEMENT_TYPE_RESULT,
    "cbst": TYPING_RESULT,
    "cgmlst": TYPING_RESULT,
    "emm": TYPING_RESULT,
    "h_type": TYPING_RESULT,
    "k_type": TYPING_RESULT,
    "lineage": TYPING_RESULT,
    "mlst": TYPING_RESULT,
    "o_type": TYPING_RESULT,
    "qc": QC_RESULT,
    "rmst": TYPING_RESULT,
    "sccmec": TYPING_RESULT,
    "shigatype": TYPING_RESULT,
    "smst": TYPING_RESULT,
    "spatype": TYPING_RESULT,
    "species": SPP_RESULT,
    "stress": ELEMENT_TYPE_RESULT,
    "stx": TYPING_RESULT,
    "virulence": TYPING_RESULT,
    "ybst": TYPING_RESULT,
}


def group_for(
    analysis_type: PrpAnalysisType, *, default_field: str | None = None
) -> str:
    """Get sample record field for analysis type.

    Raises ValueError if no mapping found and no default provided."""
    try:
        return GROUP_FOR[analysis_type]
    except KeyError:
        if default_field is None:
            raise ValueError(
                f"No group mapping for analysis type: {analysis_type.value}"
            )
        return default_field


def to_result_storage(
    sample_id: str, out: PRPParserOutput, *, pipeline_run_id: str | None
) -> AnalysisResult:
    """Convert parser ouptput to storage format."""
    envelopes = {
        atype.value: Envelope(
            status=ResultStatus(env.status.value),
            value=env.value,
            reason=env.reason,
            meta=env.meta or {},
        )
        for atype, env in out.results.items()
    }
    return AnalysisResult(
        sample_id=sample_id,
        software=out.software,
        software_version=out.software_version,
        pipeline_run_id=pipeline_run_id,
        envelopes=envelopes,
        meta={
            "parser": out.parser_name,
            "parser_version": out.parser_version,
            "schema_version": out.schema_version,
        },
    )


async def ingest_analysis_service(
    db,
    *,
    sample_id: str,
    software: str,
    file: UploadFile,
    force: bool = False,
    pipeline_run: str | None = None,
    software_version: str | None,
    ctx: ApiRequestContext | None = None,
    audit: AuditLogClient | None = None,
) -> str:
    """Parse submitted analysis file and persist an analysis record.

    Analysis results are stored in the analysis collection and denormalized into the sample record.

    Raise AnalysisExistError if an duplicate analysis for the same software exists and `force` is False.

    Raises EntryNotFound (via get_sample) if sample not present.
    """
    # ensure sample exists
    if not await sample_exists(db, sample_id=sample_id):
        raise EntryNotFound(f"Sample with id '{sample_id}' not found")

    exists = await analysis_exists(
        db,
        sample_id=sample_id,
        software=software,
        software_version=software_version,
        pipeline_run=pipeline_run,
    )
    if exists and not force:
        raise AnalysisExistsError(
            f"Analysis for sample {sample_id} with software {software} "
            f"version {software_version} and pipeline run {pipeline_run} already exists."
        )

    # Execute parser
    try:
        sync_stream = await file.read()
        out = run_parser(software=software, version=software_version, data=sync_stream)

        # cast to storage format
        doc: AnalysisResult = to_result_storage(
            sample_id=sample_id, out=out, pipeline_run_id=pipeline_run
        )
    except ParserError as exc:
        LOG.error(
            "Error when parsersing %s result for %s",
            software,
            sample_id,
            extra={"error": str(exc), "data": file.filename},
        )
        raise
    except ValidationError as ve:
        LOG.error(
            "Validation error when processing %s result for %s: %s",
            software,
            sample_id,
            str(ve),
            extra={"data": file.filename},
        )
        raise InvalidDataFormat(
            f"Validation error when processing parser output: {str(ve)}"
        ) from ve

    # audit event
    if isinstance(audit, AuditLogClient):
        subject = Subject(id=sample_id, type=SourceType.USR)
        event = EventCreate(
            source_service="bonsai_api",
            event_type="ingest_analysis",
            actor=ctx.actor if ctx else None,
            subject=subject,
            metadata={
                "software": software,
                "version": software_version,
                "pipeline_run": pipeline_run,
            },
        )
        audit.post_event(event)

    # Store canonical + denormalize view entries atomically
    envelopes_summary: dict[str, dict[str, str | None]] = {}

    # store analysis record in database
    async with managed_transaction(db.client) as txn:
        # insert canonical analysis record
        await create_analysis(
            db, doc=doc.model_dump(exclude_none=True), session=txn
        )
        analysis_id = doc.id

        # Denormalize each envelope into the approprate sample array
        for atype, env in doc.envelopes.items():
            envelopes_summary[atype] = {
                "status": env.status,
                "reason": env.reason,
            }

            result_view = AnalysisViewEntry(
                software=doc.software,
                software_version=doc.software_version,
                analysis_type=atype,
                analysis_id=analysis_id,
                pipeline_run_id=doc.pipeline_run_id,
                status=env.status,
                reason=env.reason,
                meta=env.meta or {},
                result=env.value,
                summary={},
            )
            field_name = group_for(atype)
            await upsert_analysis_results(
                db,
                sample_id=sample_id,
                field_name=field_name,
                item=result_view.model_dump(exclude_none=True),
                session=txn,
            )

    LOG.info("Ingested analysis %s for %s", analysis_id, sample_id)
    return {
        "analysis_id": analysis_id,
        "software": doc.software,
        "software_version": doc.software_version,
        "pipeline_run_id": doc.pipeline_run_id,
        "envelopes": envelopes_summary,
    }
