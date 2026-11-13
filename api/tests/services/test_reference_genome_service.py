"""A reference genome resolves by its own id, its assembly accession or a sequence accession."""

import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from bonsai_api.exceptions import EntryNotFound
from bonsai_api.services import reference_genomes

GENOME_ID = "01a0c39b-9440-7ce2-8188-08d85f0c5ecb"
ACCESSION = "GCF_000012045.1"
SEQUENCE_ACCESSION = "NC_002951.2"

DOC = {
    "id": GENOME_ID,
    "name": "Staphylococcus aureus subsp. aureus COL",
    "accession": ACCESSION,
    "organism": "Staphylococcus aureus",
    "sequence_accessions": [SEQUENCE_ACCESSION],
    "fasta_resource": "GCF_000012045.1.fasta",
    "fasta_index_resource": "GCF_000012045.1.fasta.fai",
    "reference_tracks": [],
    "created_at": datetime.datetime(2026, 1, 1),
}


@pytest.fixture(name="request_stub")
def request_stub_fixture():
    """Stand in for the FastAPI request used to build resource URLs."""
    return SimpleNamespace(url_for=lambda *args, **kwargs: "http://testserver/files/x")


def _lookups(monkeypatch, *, by_id=None, by_accession=None, by_sequence=None):
    """Patch the three crud lookups and return them for call assertions."""
    calls = SimpleNamespace(
        by_id=AsyncMock(return_value=by_id),
        by_accession=AsyncMock(return_value=by_accession),
        by_sequence=AsyncMock(return_value=by_sequence),
    )
    crud = SimpleNamespace(
        get_reference_genome_by_id=calls.by_id,
        get_reference_genome_by_accession=calls.by_accession,
        get_reference_genome_by_sequence_accession=calls.by_sequence,
    )
    monkeypatch.setattr(reference_genomes, "reference_genome_crud", crud)
    return calls


@pytest.mark.asyncio
async def test_resolves_by_internal_id_without_further_lookups(monkeypatch, request_stub):
    calls = _lookups(monkeypatch, by_id=DOC)

    genome = await reference_genomes.get_reference_genome_service(
        SimpleNamespace(), resource_id=GENOME_ID, request=request_stub
    )

    assert genome.id == GENOME_ID
    calls.by_accession.assert_not_awaited()
    calls.by_sequence.assert_not_awaited()


@pytest.mark.asyncio
async def test_falls_back_to_the_assembly_accession(monkeypatch, request_stub):
    calls = _lookups(monkeypatch, by_accession=DOC)

    genome = await reference_genomes.get_reference_genome_service(
        SimpleNamespace(), resource_id=ACCESSION, request=request_stub
    )

    assert genome.id == GENOME_ID
    calls.by_sequence.assert_not_awaited()


@pytest.mark.asyncio
async def test_falls_back_to_a_sequence_accession(monkeypatch, request_stub):
    _lookups(monkeypatch, by_sequence=DOC)

    genome = await reference_genomes.get_reference_genome_service(
        SimpleNamespace(), resource_id=SEQUENCE_ACCESSION, request=request_stub
    )

    assert genome.id == GENOME_ID


@pytest.mark.asyncio
async def test_unknown_identifier_raises_entry_not_found(monkeypatch, request_stub):
    _lookups(monkeypatch)

    with pytest.raises(EntryNotFound):
        await reference_genomes.get_reference_genome_service(
            SimpleNamespace(), resource_id="nope", request=request_stub
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("identifier", "found_by"),
    [(GENOME_ID, "by_id"), (ACCESSION, "by_accession"), (SEQUENCE_ACCESSION, "by_sequence")],
)
async def test_every_identifier_reports_the_same_canonical_id(
    monkeypatch, request_stub, identifier, found_by
):
    """Whichever identifier is used, the response carries the genome's own id."""
    _lookups(monkeypatch, **{found_by: DOC})

    genome = await reference_genomes.get_reference_genome_service(
        SimpleNamespace(), resource_id=identifier, request=request_stub
    )

    assert genome.id == GENOME_ID
    assert genome.accession == ACCESSION
