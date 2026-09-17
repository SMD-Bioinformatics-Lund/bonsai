"""Tests for analysis ingestion behavior."""

import asyncio
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bonsai_api.exceptions import AnalysisExistsError
from bonsai_api.services import analysis_service


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
