"""An IGV track records the reference genome's own id, whichever identifier was supplied."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from bonsai_api.exceptions import ConflictError, EntryNotFound
from bonsai_api.models.genomic_resource import GenomicResourceCreate
from bonsai_api.services import genomic_resource_service

GENOME_ID = "01a0c39b-9440-7ce2-8188-08d85f0c5ecb"
ACCESSION = "GCF_000012045.1"
SAMPLE_ID = "01a0c3a1-1111-7000-9000-aaaaaaaaaaaa"

GENOME = SimpleNamespace(id=GENOME_ID, accession=ACCESSION)


@pytest.fixture(name="request_stub")
def request_stub_fixture():
    return SimpleNamespace(url_for=lambda *args, **kwargs: "http://testserver/files/x")


def _resource(identifier: str) -> GenomicResourceCreate:
    return GenomicResourceCreate.model_validate(
        {
            "reference_genome_id": identifier,
            "pipeline_run_id": "run-1",
            "resource_data": [
                {
                    "name": "Read coverage",
                    "format": "bam",
                    "type": "alignment",
                    "path": "saureus/bam/s1.bam",
                }
            ],
        }
    )


def _collaborators(monkeypatch, *, genome=GENOME, has_resource=False):
    """Patch the service's collaborators and return the insert mock."""
    monkeypatch.setattr(
        genomic_resource_service, "sample_exists", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        genomic_resource_service,
        "sample_has_resource",
        AsyncMock(return_value=has_resource),
    )
    resolve = (
        AsyncMock(side_effect=genome)
        if isinstance(genome, Exception)
        else AsyncMock(return_value=genome)
    )
    monkeypatch.setattr(
        genomic_resource_service, "get_reference_genome_service", resolve
    )
    monkeypatch.setattr(
        genomic_resource_service, "to_relative_resource", lambda path, base_dir: path
    )
    monkeypatch.setattr(
        genomic_resource_service, "resolve_resource_url", lambda *a, **k: "http://x/f"
    )
    insert = AsyncMock(return_value=None)
    monkeypatch.setattr(genomic_resource_service, "insert_genomic_resource", insert)
    return insert


async def _run(request_stub, identifier, force=False):
    return await genomic_resource_service.create_genomic_resource_service(
        SimpleNamespace(),
        sample_id=SAMPLE_ID,
        request=request_stub,
        force=force,
        resource=_resource(identifier),
        ctx=SimpleNamespace(),
        audit=None,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("identifier", [ACCESSION, GENOME_ID])
async def test_a_track_records_the_canonical_reference_genome_id(
    monkeypatch, request_stub, identifier
):
    insert = _collaborators(monkeypatch)

    responses = await _run(request_stub, identifier)

    stored = insert.await_args.kwargs["resource_data"]
    assert [r["reference_genome_id"] for r in stored] == [GENOME_ID]
    assert [r.reference_genome_id for r in responses] == [GENOME_ID]


@pytest.mark.asyncio
async def test_an_unknown_reference_genome_is_rejected_without_inserting(
    monkeypatch, request_stub
):
    insert = _collaborators(monkeypatch, genome=EntryNotFound("nope"))

    with pytest.raises(EntryNotFound):
        await _run(request_stub, "nope")

    insert.assert_not_awaited()


@pytest.mark.asyncio
async def test_existing_pipeline_resources_require_force(monkeypatch, request_stub):
    insert = _collaborators(monkeypatch, has_resource=True)

    with pytest.raises(ConflictError):
        await _run(request_stub, ACCESSION)

    insert.assert_not_awaited()


@pytest.mark.asyncio
async def test_force_replaces_resources_for_the_same_pipeline(monkeypatch, request_stub):
    insert = _collaborators(monkeypatch, has_resource=True)

    await _run(request_stub, ACCESSION, force=True)

    assert insert.await_args.kwargs["replace"] is True
