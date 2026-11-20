"""A sample records the reference genome's own id, whichever identifier was supplied."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from bonsai_api.exceptions import EntryNotFound
from bonsai_api.services import sample_service
from pymongo.results import UpdateResult

GENOME_ID = "01a0c39b-9440-7ce2-8188-08d85f0c5ecb"
ACCESSION = "GCF_000012045.1"
SEQUENCE_ACCESSION = "NC_002951.2"
SAMPLE_ID = "01a0c3a1-1111-7000-9000-aaaaaaaaaaaa"

GENOME = SimpleNamespace(
    id=GENOME_ID,
    name="Staphylococcus aureus subsp. aureus COL",
    accession=ACCESSION,
    sequence_accessions=[SEQUENCE_ACCESSION],
    fasta_url="http://testserver/files/reference-genomes/g.fasta",
    fasta_index_url="http://testserver/files/reference-genomes/g.fasta.fai",
    reference_tracks=[],
)


@pytest.fixture(name="request_stub")
def request_stub_fixture():
    return SimpleNamespace(url_for=lambda *args, **kwargs: "http://testserver/files/x")


def _attach(
    monkeypatch, *, genome=GENOME, sample_found=True, matched_count=1, modified_count=1
):
    """Patch the collaborators of add_reference_genome_service and return the writer."""
    monkeypatch.setattr(
        sample_service, "sample_exists", AsyncMock(return_value=sample_found)
    )
    resolve = AsyncMock(return_value=genome)
    if isinstance(genome, Exception):
        resolve = AsyncMock(side_effect=genome)
    monkeypatch.setattr(sample_service, "get_reference_genome_service", resolve)
    writer = AsyncMock(
        return_value=UpdateResult(
            {"n": matched_count, "nModified": modified_count}, acknowledged=True
        )
    )
    monkeypatch.setattr(sample_service, "add_reference_genome_to_sample", writer)
    return writer


async def _run(request_stub, identifier):
    return await sample_service.add_reference_genome_service(
        SimpleNamespace(),
        sample_id=SAMPLE_ID,
        reference_genome_id=identifier,
        ctx=SimpleNamespace(),
        request=request_stub,
        audit=None,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("identifier", [ACCESSION, SEQUENCE_ACCESSION, GENOME_ID])
async def test_any_identifier_is_stored_as_the_canonical_id(
    monkeypatch, request_stub, identifier
):
    """An accession must not end up in reference_genome_id; the genome's id must."""
    writer = _attach(monkeypatch)

    await _run(request_stub, identifier)

    assert writer.await_args.kwargs["reference_genome_id"] == GENOME_ID


@pytest.mark.asyncio
async def test_an_unknown_reference_genome_is_rejected_without_writing(
    monkeypatch, request_stub
):
    writer = _attach(monkeypatch, genome=EntryNotFound("nope"))

    with pytest.raises(EntryNotFound):
        await _run(request_stub, "nope")

    writer.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("sample_found", [False, True])
async def test_a_missing_sample_is_rejected(monkeypatch, request_stub, sample_found):
    """Reject a missing sample, including one deleted before the update."""
    writer = _attach(
        monkeypatch, sample_found=sample_found, matched_count=0, modified_count=0
    )

    with pytest.raises(EntryNotFound):
        await _run(request_stub, ACCESSION)

    if sample_found:
        writer.assert_awaited_once()
    else:
        writer.assert_not_awaited()


@pytest.mark.asyncio
async def test_reattaching_the_same_genome_succeeds(monkeypatch, request_stub, caplog):
    """An unchanged assignment returns the genome and logs the zero modification count."""
    _attach(monkeypatch, modified_count=0)

    with caplog.at_level("INFO", logger=sample_service.__name__):
        result = await _run(request_stub, ACCESSION)

    assert result is GENOME
    assert f"sample_id={SAMPLE_ID}" in caplog.text
    assert f"reference_genome_id={GENOME_ID}" in caplog.text
    assert "matched_count=1 modified_count=0" in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("stored", [ACCESSION, GENOME_ID])
async def test_igv_config_resolves_however_the_reference_was_stored(
    monkeypatch, request_stub, stored
):
    """Rows written before ids were normalised still resolve, so nothing is missed."""
    monkeypatch.setattr(
        sample_service,
        "get_sample_service",
        AsyncMock(return_value=SimpleNamespace(reference_genome_id=stored)),
    )
    resolve = AsyncMock(return_value=GENOME)
    monkeypatch.setattr(sample_service, "get_reference_genome_service", resolve)
    monkeypatch.setattr(
        sample_service,
        "list_genomic_resources_for_sample_service",
        AsyncMock(return_value=[]),
    )

    config = await sample_service.get_igv_config(
        SimpleNamespace(), sample_id=SAMPLE_ID, request=request_stub
    )

    assert resolve.await_args.kwargs["resource_id"] == stored
    assert config.reference.name == GENOME.name


@pytest.mark.asyncio
async def test_igv_config_rejects_a_sample_without_a_reference_genome(
    monkeypatch, request_stub
):
    monkeypatch.setattr(
        sample_service,
        "get_sample_service",
        AsyncMock(return_value=SimpleNamespace(reference_genome_id=None)),
    )

    with pytest.raises(EntryNotFound):
        await sample_service.get_igv_config(
            SimpleNamespace(), sample_id=SAMPLE_ID, request=request_stub
        )
