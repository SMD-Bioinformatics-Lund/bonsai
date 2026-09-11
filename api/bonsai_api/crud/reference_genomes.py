"""Reference genome CRUD operations."""

import logging
from typing import Any

from pymongo.client_session import ClientSession


from bonsai_api.db import Database

LOG = logging.getLogger(__name__)


async def get_reference_genome_by_accession(
    db: Database,
    *,
    accession: str,
    session: ClientSession | None = None,
) -> dict[str, Any] | None:
    """Get a reference genome by its assembly accession."""
    return await db.reference_genome_collection.find_one(
        {"accession": accession}, session=session
    )


async def get_reference_genome_by_sequence_accession(
    db: Database,
    *,
    sequence_accession: str,
    session: ClientSession | None = None,
) -> dict[str, Any] | None:
    """Get a reference genome containing the given sequence accession."""
    return await db.reference_genome_collection.find_one(
        {"sequence_accessions": sequence_accession}, session=session
    )


async def list_reference_genomes_service(db: Database):
    """List available reference genomes."""
    return await db.reference_genome_collection.find().to_list(length=None)


async def insert_reference_genome_document(
    db: Database,
    *,
    doc: dict[str, Any],
    session: ClientSession | None = None,
) -> str:
    """Create a new document in the reference genome collection."""
    LOG.debug("Creating reference genome document", extra={"doc": doc})
    return await db.reference_genome_collection.insert_one(doc, session=session)
