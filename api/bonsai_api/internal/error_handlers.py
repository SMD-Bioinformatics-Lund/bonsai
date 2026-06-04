"""Custom FastAPI error handlers."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from typing import Any

from bonsai_api.exceptions import (
    AuditLogError,
    ConflictError,
    NotChangedError,
    ParserError,
    EntryNotFound,
    UnsupportedSoftwareError,
    UnsupportedVersionError,
    UnsupportedAnalysisTypeError,
    InvalidDataFormat,
    SchemaMismatchError,
    AnalysisExistsError,
)
from .problem_types import (
    ANALYSIS_DUPLICATED,
    AUDIT_LOG_UNAVAILABLE,
    CONFLICT,
    INVALID_DATA,
    NOT_FOUND,
    NOT_IMPLEMENTED,
    NOT_MODIFIED,
    PARSER_ERROR,
    SCHEMA_MISMATCH,
    UNSUPPORTED_ANALYSIS,
    UNSUPPORTED_SOFTWARE,
    UNSUPPORTED_VERSION,
)


def problem_details(
    status: int,
    title: str,
    detail: str,
    *,
    type_: str = "about:blank",
    instance: str | None = None,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": type_,
        "title": title,
        "status": status,
        "detail": detail,
    }
    if instance:
        body["instance"] = instance
    if extra:
        body.update(extra)
    return JSONResponse(status_code=status, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    """Register handlers for custom exceptions."""

    @app.exception_handler(EntryNotFound)
    async def _not_found(_: Request, exc: EntryNotFound):
        return problem_details(404, "Not Found", str(exc), type_=NOT_FOUND)


    @app.exception_handler(NotChangedError)
    async def _not_modified(_: Request, exc: NotChangedError):
        return problem_details(304, "Not modified", str(exc), type_=NOT_MODIFIED)


    @app.exception_handler(FileNotFoundError)
    async def _file_not_found(_: Request, exc: FileNotFoundError):
        return problem_details(404, "Not Found", str(exc), type_=NOT_FOUND)
    

    @app.exception_handler(UnsupportedSoftwareError)
    async def _unsupported_software(_: Request, exc: UnsupportedSoftwareError):
        return problem_details(400, "Unsupported software", str(exc), type_=UNSUPPORTED_SOFTWARE)
    

    @app.exception_handler(UnsupportedVersionError)
    async def _unsupported_software_version(_: Request, exc: UnsupportedVersionError):
        return problem_details(400, "Unsupported software version", str(exc), type_=UNSUPPORTED_VERSION)


    @app.exception_handler(UnsupportedAnalysisTypeError)
    async def _unsupported_analysis_type(_: Request, exc: UnsupportedAnalysisTypeError):
        return problem_details(422, "Unsupported analysis type", str(exc), type_=UNSUPPORTED_ANALYSIS)


    @app.exception_handler(InvalidDataFormat)
    async def _invalid_data_format(_: Request, exc: InvalidDataFormat):
        return problem_details(422, "Invalid data format", str(exc), type_=INVALID_DATA)


    @app.exception_handler(SchemaMismatchError)
    async def _schema_mismatch_error(_: Request, exc: SchemaMismatchError):
        return problem_details(422, "Schema mismatch", str(exc), type_=SCHEMA_MISMATCH)


    @app.exception_handler(ConflictError)
    async def _conflict(_: Request, exc: ConflictError):
        return problem_details(409, "Conflict", str(exc), type_=CONFLICT,
                               extra={"context": getattr(exc, "context", {})})

    @app.exception_handler(AuditLogError)
    async def _audit_log_error(_: Request, exc: AuditLogError):
        return problem_details(
            503,
            "Audit log unavailable",
            str(exc),
            type_=AUDIT_LOG_UNAVAILABLE,
        )

    @app.exception_handler(ParserError)
    async def _parser_error(_: Request, exc: ParserError):
        # Catch-all for parse failures that weren’t matched above
        return problem_details(500, "Parser error", str(exc), type_=PARSER_ERROR,
                               extra={"context": getattr(exc, "context", {})})

    @app.exception_handler(AnalysisExistsError)
    async def _analysis_exists(_: Request, exc: AnalysisExistsError):
        return problem_details(409, "", str(exc), type_=ANALYSIS_DUPLICATED)


    @app.exception_handler(NotImplementedError)
    async def _not_implemented(_: Request, exc: NotImplementedError):
        return problem_details(501, "Not Implemented", str(exc), type_=NOT_IMPLEMENTED)