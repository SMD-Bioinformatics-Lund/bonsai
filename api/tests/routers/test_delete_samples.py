"""Deleting a batch of samples skips ids that no longer exist."""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from bonsai_api.routers.samples import samples as samples_router


@asynccontextmanager
async def _transaction(_client, _session=None):
    yield SimpleNamespace(abort_transaction=lambda: None)


def _collaborators(monkeypatch, *, missing):
    """Patch the route's collaborators, returning the delete mock."""
    monkeypatch.setattr(samples_router, "managed_transaction", _transaction)
    monkeypatch.setattr(
        samples_router, "check_samples_exists", AsyncMock(return_value=set(missing))
    )
    delete = AsyncMock(
        side_effect=lambda db, sample_id, session=None: {
            "removed_sample": True,
            "remove_sourmash": f"job-{sample_id}",
            "remove_sourmash_idx": f"idx-{sample_id}",
        }
    )
    monkeypatch.setattr(samples_router, "delete_sample_service", delete)
    return delete


async def _run(sample_ids):
    return await samples_router.delete_many_samples(
        sample_ids=sample_ids,
        db=SimpleNamespace(client=None),
        audit_log=None,
        req_ctx=SimpleNamespace(actor=None, metadata=None),
        current_user=None,
    )


@pytest.mark.asyncio
async def test_a_stale_id_does_not_block_the_rest_of_the_batch(monkeypatch):
    delete = _collaborators(monkeypatch, missing={"gone"})

    result = await _run(["keep-1", "gone", "keep-2"])

    assert [call.kwargs["sample_id"] for call in delete.await_args_list] == ["keep-1", "keep-2"]
    assert result["n_deleted"] == 2
    assert result["missing_sample_ids"] == ["gone"]
    assert result["remove_signature_jobs"] == ["job-keep-1", "job-keep-2"]


@pytest.mark.asyncio
async def test_all_ids_missing_deletes_nothing_and_reports_them(monkeypatch):
    delete = _collaborators(monkeypatch, missing={"gone-1", "gone-2"})

    result = await _run(["gone-1", "gone-2"])

    delete.assert_not_awaited()
    assert result["n_deleted"] == 0
    assert result["missing_sample_ids"] == ["gone-1", "gone-2"]


@pytest.mark.asyncio
async def test_every_id_present_deletes_them_all(monkeypatch):
    delete = _collaborators(monkeypatch, missing=set())

    result = await _run(["keep-1", "keep-2"])

    assert delete.await_count == 2
    assert result["n_deleted"] == 2
    assert result["missing_sample_ids"] == []
