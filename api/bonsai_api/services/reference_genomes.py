"""Service functions for managing reference genomes."""

import logging
from typing import Any

from pathlib import Path

from pydantic import ValidationError
from pymongo.errors import PyMongoError
from fastapi import Request

from bonsai_api.crud.utils import managed_transaction
from bonsai_api.exceptions import DatabaseOperationError, EntryNotFound, GenomeResourceError
from bonsai_api.db import Database
from bonsai_api.models.genomic_resource import ResourceOutput
from bonsai_api.models.reference_genome import ReferenceGenomeCreate, ReferenceGenomeDb, ReferenceGenomeResponse
from bonsai_api.models.enums import FileSources

import bonsai_api.crud.reference_genomes as reference_genome_crud
from bonsai_api.io import to_relative_resource, validate_resource_identifier
from bonsai_api.config import settings

from .utils import resolve_resource_url

LOG = logging.getLogger(__name__)


def _to_ref_genome_output(request: Request, doc: dict[str, Any]) -> ReferenceGenomeResponse:
    tracks = [
        ResourceOutput(
            url=resolve_resource_url(request, FileSources.REFERENCE_GENOMES, track["path"]),
            index_url=resolve_resource_url(request, FileSources.REFERENCE_GENOMES, track["index_path"]) if track.get("index_url") else None,
            format=track["format"],
            type=track["type"],
            name=track["name"],
        ) 
        for track in doc.get("reference_tracks", [])]
    return ReferenceGenomeResponse(
            id=doc["id"],
            name=doc["name"],
            accession=doc["accession"],
            organism=doc["organism"],
            fasta_url=resolve_resource_url(request, FileSources.REFERENCE_GENOMES, doc["fasta_resource"]),
            fasta_index_url=resolve_resource_url(request, FileSources.REFERENCE_GENOMES, doc["fasta_index_resource"]),
            reference_tracks=tracks,
            created_at=doc["created_at"].isoformat() if doc.get("created_at") else None,
    )


async def get_reference_genome_service(
    db: Database,
    *,
    resource_id: str,
    request: Request,
) -> ReferenceGenomeResponse:
    """Get a reference genome by ID."""
    try:
        doc = await reference_genome_crud.get_reference_genome_by_id(db, resource_id=resource_id)

        if not doc:
            raise EntryNotFound(f"Reference genome with ID {resource_id} not found")
        return _to_ref_genome_output(request, doc)
    except PyMongoError as pme:
        LOG.error("MongoDB error while fetching reference genome: %s", str(pme))
        raise DatabaseOperationError(
            f"Database error occurred while fetching reference genome: {str(pme)}"
        ) from pme
    except ValidationError as ve:
        LOG.error("Validation error fetching reference genome: %s", str(ve))
        raise ValueError(
            f"Invalid data provided for fetching reference genome: {str(ve)}"
        ) from ve


async def list_reference_genomes_service(
    db: Database,
    *,
    request: Request,
) -> list[ReferenceGenomeResponse]:
    """List available reference genomes."""
    try:
        docs = await reference_genome_crud.list_reference_genomes_service(db)
        return [_to_ref_genome_output(request, doc) for doc in docs]
    except PyMongoError as pme:
        LOG.error("MongoDB error while fetching reference genomes: %s", str(pme))
        raise DatabaseOperationError(
            f"Database error occurred while fetching reference genomes: {str(pme)}"
        ) from pme
    except ValidationError as ve:
        LOG.error("Validation error fetching reference genomes: %s", str(ve))
        raise ValueError(
            f"Invalid data provided for fetching reference genomes: {str(ve)}"
        ) from ve
    except PyMongoError as pme:
        LOG.error("MongoDB error while fetching reference genomes: %s", str(pme))
        raise DatabaseOperationError(
            f"Database error occurred while fetching reference genomes: {str(pme)}"
        ) from pme
    except ValidationError as ve:
        LOG.error("Validation error fetching reference genomes: %s", str(ve))
        raise ValueError(
            f"Invalid data provided for fetching reference genomes: {str(ve)}"
        ) from ve


async def create_reference_genome_service(
    db: Database,
    *,
    reference_genome: ReferenceGenomeCreate,
    request: Request,
) -> ReferenceGenomeResponse:
    """Create a new reference genome."""
    # build ref genome payload
    try:
        # build list of resources to validate and convert to relative paths
        to_validate = [reference_genome.fasta_resource, reference_genome.fasta_index_resource]
        for track in reference_genome.reference_tracks:
            to_validate.append(track.path)
            to_validate.append(track.index_path)
        for r in to_validate:
            if r:
                validate_resource_identifier(r)

        base_path = Path(settings.reference_genomes_dir)
        async with managed_transaction(db.client) as txn:
            payload = ReferenceGenomeDb(
                name=reference_genome.name,
                accession=reference_genome.accession,
                organism=reference_genome.organism,
                fasta_resource=str(to_relative_resource(reference_genome.fasta_resource, base_path)),
                fasta_index_resource=str(to_relative_resource(reference_genome.fasta_index_resource, base_path)),
                reference_tracks=reference_genome.reference_tracks,
            )
            await reference_genome_crud.insert_reference_genome_document(db, doc=payload.model_dump(), session=txn)
            return _to_ref_genome_output(request, payload.model_dump())
    except PyMongoError as pme:
        LOG.error("MongoDB error while creating reference genome: %s", str(pme))
        raise DatabaseOperationError(
            f"Database error occurred while creating reference genome: {str(pme)}"
        ) from pme
    except ValidationError as ve:
        LOG.error("Validation error creating reference genome: %s", str(ve))
        raise ValueError(
            f"Invalid data provided for creating reference genome: {str(ve)}"
        ) from ve
    except GenomeResourceError as gre:
        LOG.error("Error resolving genome resource: %s", str(gre))
        raise FileNotFoundError(
            f"Error resolving genome resource: {str(gre)}"
        ) from gre
