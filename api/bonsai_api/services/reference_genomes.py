"""Service functions for managing reference genomes."""

import logging

from pathlib import Path

from pydantic import ValidationError
from pymongo.errors import PyMongoError
from fastapi import Request

from bonsai_api.exceptions import DatabaseOperationError, GenomeResourceError
from bonsai_api.db import Database
from bonsai_api.models.reference_genome import ReferenceGenomeCreate, ReferenceGenomeDb, ReferenceGenomeResponse

import bonsai_api.crud.reference_genomes as reference_genome_crud
from bonsai_api.io import resolve_genome_resource
from bonsai_api.config import settings


LOG = logging.getLogger(__name__)


def resolve_resource_url(resource: str) -> str:
    """Resolve a resource URI to an accessible URL."""
    return Request.url_for('genome-resource', file=resource)


async def list_reference_genomes_service(
    db: Database,
) -> list[ReferenceGenomeResponse]:
    """List available reference genomes."""
    try:
        docs = await reference_genome_crud.list_reference_genomes_service(db)
        return [
            ReferenceGenomeResponse(
                id=str(doc["_id"]),
                name=doc["name"],
                accession=doc["accession"],
                organism=doc["organism"],
                fasta_url=resolve_resource_url(doc["fasta_resource"]),
                fasta_index_url=resolve_resource_url(doc["fasta_index_resource"]),
                genome_annotation_url=resolve_resource_url(doc["genome_annotation_resource"]) if doc.get("genome_annotation_resource") else None,
                created_at=doc["created_at"].isoformat() if doc.get("created_at") else None,
            ) for doc in docs]
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
) -> ReferenceGenomeResponse:
    """Create a new reference genome."""
    # build ref genome payload
    try:
        base_path = Path(settings.reference_genomes_dir)
        payload = ReferenceGenomeDb(
            name=reference_genome.name,
            accession=reference_genome.accession,
            organism=reference_genome.organism,
            fasta_resource=resolve_genome_resource(reference_genome.fasta_resource, base_path),
            fasta_index_resource=resolve_genome_resource(reference_genome.fasta_index_resource, base_path),
            genome_annotation_resource=resolve_genome_resource(reference_genome.genome_annotation_resource, base_path) if reference_genome.genome_annotation_resource else None,
        )
        result = await reference_genome_crud.insert_reference_genome_document(db, doc=payload.model_dump())
        return ReferenceGenomeResponse.model_validate(result)
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
