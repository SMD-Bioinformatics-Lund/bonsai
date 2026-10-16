"""Tests for analysis ingestion behavior."""

import asyncio
from contextlib import asynccontextmanager
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from bonsai_api.exceptions import AnalysisExistsError, InvalidDataFormat
from bonsai_api.services import analysis_service
from bonsai_libs.parse.models.base import ParserOutput, ResultEnvelope
from bonsai_libs.parse.models.enums import AnalysisType, ResultStatus


@pytest.mark.parametrize("software", ["resfinder", "mlst", "mixed"])
@pytest.mark.parametrize("force", [False, True])
def test_failed_parse_never_writes(monkeypatch, software, force):
    """Failed reparses must not insert records or replace the sample view."""
    create = AsyncMock()
    upsert = AsyncMock()
    transaction = Mock()
    audit = Mock(spec=analysis_service.AuditLogClient)
    monkeypatch.setattr(analysis_service, "sample_exists", AsyncMock(return_value=True))
    monkeypatch.setattr(
        analysis_service, "analysis_exists", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(analysis_service, "create_analysis", create)
    monkeypatch.setattr(analysis_service, "upsert_analysis_results", upsert)
    monkeypatch.setattr(analysis_service, "managed_transaction", transaction)

    if software == "mixed":
        output = ParserOutput(
            software="resfinder",
            software_version="1.0.0",
            parser_name="test",
            parser_version=1,
            results={
                AnalysisType.AMR: ResultEnvelope(status=ResultStatus.EMPTY),
                AnalysisType.STRESS: ResultEnvelope(
                    status=ResultStatus.ERROR, reason="Broken stress result"
                ),
            },
        )
        monkeypatch.setattr(analysis_service, "run_parser", lambda **_: output)

    upload = SimpleNamespace(file=BytesIO(b'{"truncated":'), filename="result.json")
    with pytest.raises(InvalidDataFormat, match="Failed to parse"):
        asyncio.run(
            analysis_service.ingest_analysis_service(
                SimpleNamespace(),
                sample_id="sample-1",
                software=software,
                software_version="1.0.0",
                pipeline_run="run-1",
                file=upload,
                force=force,
                audit=audit,
            )
        )

    create.assert_not_awaited()
    upsert.assert_not_awaited()
    transaction.assert_not_called()
    audit.post_event.assert_not_called()


@pytest.mark.parametrize("status", [ResultStatus.EMPTY, ResultStatus.ABSENT])
def test_legitimate_no_result_can_still_be_ingested(monkeypatch, status):
    """The error guard must preserve successful no-findings/no-call uploads."""
    output = ParserOutput(
        software="mlst",
        software_version="1.0.0",
        parser_name="test",
        parser_version=1,
        results={AnalysisType.MLST: ResultEnvelope(status=status)},
    )
    create = AsyncMock()
    upsert = AsyncMock()

    @asynccontextmanager
    async def transaction(_):
        yield None

    monkeypatch.setattr(analysis_service, "run_parser", lambda **_: output)
    monkeypatch.setattr(analysis_service, "sample_exists", AsyncMock(return_value=True))
    monkeypatch.setattr(
        analysis_service, "analysis_exists", AsyncMock(return_value=False)
    )
    monkeypatch.setattr(analysis_service, "create_analysis", create)
    monkeypatch.setattr(analysis_service, "upsert_analysis_results", upsert)
    monkeypatch.setattr(analysis_service, "managed_transaction", transaction)

    response = asyncio.run(
        analysis_service.ingest_analysis_service(
            SimpleNamespace(client=None),
            sample_id="sample-1",
            software="mlst",
            software_version="1.0.0",
            file=SimpleNamespace(file=BytesIO(b"input"), filename="result.json"),
        )
    )

    assert response["envelopes"]["mlst"]["status"] == status.value
    create.assert_awaited_once()
    upsert.assert_awaited_once()


def test_duplicate_check_uses_normalized_parser_software(monkeypatch):
    """Parser aliases must be checked under the identity stored in MongoDB."""
    parser_output = SimpleNamespace(
        results={},
        software="postalignqc",
        software_version="1.2.3",
        parser_name="post-align-qc",
        parser_version="1",
        schema_version=1,
    )
    analysis_exists = AsyncMock(return_value=True)
    monkeypatch.setattr(analysis_service, "sample_exists", AsyncMock(return_value=True))
    monkeypatch.setattr(analysis_service, "analysis_exists", analysis_exists)
    monkeypatch.setattr(analysis_service, "run_parser", lambda **_: parser_output)
    monkeypatch.setattr(analysis_service, "RUN_PARSER_SUPPORTS_SUBCOMMAND", True)

    upload = SimpleNamespace(file=BytesIO(b"input"), filename="stats.txt")
    with pytest.raises(AnalysisExistsError, match="postalignqc.stats"):
        asyncio.run(
            analysis_service.ingest_analysis_service(
                SimpleNamespace(),
                sample_id="sample-1",
                software="samtools",
                subcommand="stats",
                software_version="1.2.3",
                pipeline_run="run-1",
                file=upload,
            )
        )

    analysis_exists.assert_awaited_once_with(
        SimpleNamespace(),
        sample_id="sample-1",
        software="postalignqc",
        subcommand="stats",
        software_version="1.2.3",
        pipeline_run="run-1",
    )
