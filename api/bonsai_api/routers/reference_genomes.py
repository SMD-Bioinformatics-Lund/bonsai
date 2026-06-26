"""Manage reference genomes for samples."""

import logging

from fastapi import APIRouter, Depends, Request, Security

from bonsai_api.services.reference_genomes import list_reference_genomes_service, create_reference_genome_service
from bonsai_api.models.user import UserOutputDatabase
from bonsai_api.models.reference_genome import ReferenceGenomeCreate, ReferenceGenomeResponse
from bonsai_api.dependencies import get_current_active_user, get_database
from bonsai_api.db import Database

from .tags import RouterTags

LOG = logging.getLogger(__name__)

router = APIRouter(tags=[RouterTags.REFERENCE_GENOME])

WRITE_PERMISSION = "reference_genomes:write"

@router.get('/reference-genomes')
async def list_reference_genomes(
    request: Request,
    db: Database = Depends(get_database),
) -> list[ReferenceGenomeResponse]:
    """List available reference genomes."""
    return await list_reference_genomes_service(db, request=request)


@router.post('/reference-genomes')
async def create_reference_genome(
    reference_genome: ReferenceGenomeCreate,
    request: Request,
    db: Database = Depends(get_database),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
) -> ReferenceGenomeResponse:
    """Create a new reference genome."""
    return await create_reference_genome_service(db, reference_genome=reference_genome, request=request)