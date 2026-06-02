"""Public resources and constants."""

import logging

from fastapi import APIRouter

from bonsai_api.models.antibiotics import ANTIBIOTICS
from bonsai_api.models.qc import VARIANT_REJECTION_REASONS

from .tags import RouterTags

LOG = logging.getLogger(__name__)
router = APIRouter(tags=[RouterTags.REFERENCE])

READ_PERMISSION = "reference:read"


@router.get("/reference/antibiotics")
async def get_antibiotics():
    """Get antibiotic names."""
    return ANTIBIOTICS


@router.get("/reference/variant/rejection")
async def get_variant_rejection():
    """Get antibiotic names."""
    return VARIANT_REJECTION_REASONS
