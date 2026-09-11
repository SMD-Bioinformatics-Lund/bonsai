"""Tests for sample QC route behavior."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from bonsai_api.models.qc import QcClassification, SampleQcClassification
from bonsai_api.routers.samples import sample_qc


@pytest.mark.asyncio
async def test_update_qc_status_returns_classification_when_unchanged(monkeypatch):
    """An idempotent update still returns the declared response model."""
    classification = QcClassification(status=SampleQcClassification.PASSED)
    get_sample = AsyncMock(return_value=SimpleNamespace(qc_status=classification))
    monkeypatch.setattr(sample_qc, "get_sample_service", get_sample)

    result = await sample_qc.update_qc_status(
        classification,
        sample_id="sample-1",
        db=object(),
        audit_log=None,
        req_ctx=None,
        current_user=None,
    )

    assert result == classification


@pytest.mark.asyncio
async def test_update_qc_status_includes_passed_sample(monkeypatch):
    """Passing QC adds the sample to the analysis index."""
    classification = QcClassification(status=SampleQcClassification.PASSED)
    existing = QcClassification(status=SampleQcClassification.FAILED)
    monkeypatch.setattr(
        sample_qc,
        "get_sample_service",
        AsyncMock(return_value=SimpleNamespace(qc_status=existing)),
    )
    monkeypatch.setattr(
        sample_qc,
        "update_sample_qc_classification",
        AsyncMock(return_value=classification),
    )

    include = Mock(return_value=SimpleNamespace(id="include-job"))
    schedule_add = Mock()
    exclude = Mock()
    schedule_remove = Mock()
    monkeypatch.setattr(sample_qc, "include_in_analysis", include)
    monkeypatch.setattr(
        sample_qc, "schedule_add_genome_signature_to_index", schedule_add
    )
    monkeypatch.setattr(sample_qc, "exclude_from_analysis", exclude)
    monkeypatch.setattr(
        sample_qc, "schedule_remove_genome_signature_from_index", schedule_remove
    )

    result = await sample_qc.update_qc_status(
        classification,
        sample_id="sample-1",
        db=object(),
        audit_log=None,
        req_ctx=None,
        current_user=None,
    )

    assert result == classification
    include.assert_called_once_with("sample-1")
    schedule_add.assert_called_once_with(["sample-1"], depends_on=["include-job"])
    exclude.assert_not_called()
    schedule_remove.assert_not_called()
