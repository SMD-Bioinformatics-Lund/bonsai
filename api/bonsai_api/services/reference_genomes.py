"""Service functions for managing reference genomes."""

import logging

from pathlib import Path

from pydantic import ValidationError
from pymongo.errors import PyMongoError
from fastapi import Request

from bonsai_api.crud.utils import managed_transaction
from bonsai_api.exceptions import DatabaseOperationError, GenomeResourceError
from bonsai_api.db import Database
from bonsai_api.models.reference_genome import ReferenceGenomeCreate, ReferenceGenomeDb, ReferenceGenomeResponse

import bonsai_api.crud.reference_genomes as reference_genome_crud
from bonsai_api.io import to_relative_resource, validate_resource_identifier
from bonsai_api.config import settings


LOG = logging.getLogger(__name__)


def resolve_resource_url(request: Request, resource: str) -> str:
    """Resolve a resource URI to an accessible URL."""
    LOG.warning(request)
    return str(request.url_for('genome-resource', file=resource))


async def list_reference_genomes_service(
    db: Database,
    *,
    request: Request,
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
                fasta_url=resolve_resource_url(request, doc["fasta_resource"]),
                fasta_index_url=resolve_resource_url(request, doc["fasta_index_resource"]),
                genome_annotation_url=resolve_resource_url(request, doc["genome_annotation_resource"]) if doc.get("genome_annotation_resource") else None,
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
    request: Request,
) -> ReferenceGenomeResponse:
    """Create a new reference genome."""
    # build ref genome payload
    try:
        for resource in [reference_genome.fasta_resource, reference_genome.fasta_index_resource, reference_genome.genome_annotation_resource]:
            if resource:
                validate_resource_identifier(resource)

        base_path = Path(settings.reference_genomes_dir)
        async with managed_transaction(db.client) as txn:
            payload = ReferenceGenomeDb(
                name=reference_genome.name,
                accession=reference_genome.accession,
                organism=reference_genome.organism,
                fasta_resource=str(to_relative_resource(reference_genome.fasta_resource, base_path)),
                fasta_index_resource=str(to_relative_resource(reference_genome.fasta_index_resource, base_path)),
                genome_annotation_resource=str(to_relative_resource(reference_genome.genome_annotation_resource, base_path)) if reference_genome.genome_annotation_resource else None,
            )
            await reference_genome_crud.insert_reference_genome_document(db, doc=payload.model_dump(), session=txn)

            return ReferenceGenomeResponse(
                **payload.model_dump(mode="json"),
                fasta_url=resolve_resource_url(request, payload.fasta_resource),
                fasta_index_url=resolve_resource_url(request, payload.fasta_index_resource),
                genome_annotation_url=(
                    resolve_resource_url(request, payload.genome_annotation_resource)
                    if payload.genome_annotation_resource else None
                ),
            )
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
