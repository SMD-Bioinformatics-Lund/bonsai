from __future__ import annotations

from typing import Any

from bonsai_libs.jobs import ExecutionHooks, execute_task, LoggerProtocol, TracerProtocol, ExecutionContext, JobRequest, JobResponse

from .handlers import tasks_registry


def execute_service_task(
    request: dict[str, Any] | JobRequest,
    *,
    hooks: ExecutionHooks | None = None,
    logger: LoggerProtocol | None = None,
    tracer: TracerProtocol | None = None,
    context: ExecutionContext | dict[str, Any] | None = None,
) -> JobResponse:
    """
    Service-specific entrypoint that binds the minhash task registry
    to the shared job execution helper.
    """
    return execute_task(
        registry=tasks_registry,
        request=request,
        hooks=hooks,
        logger=logger,
        tracer=tracer,
        context=context,
    )