"""Public resources and constants."""

from fastapi import APIRouter
import logging

from ..models.antibiotics import ANTIBIOTICS

LOG = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_TAGS = [
    "resources",
]
READ_PERMISSION = "resources:read"

@router.get("/resources/antibiotics", tags=DEFAULT_TAGS)
async def get_antibiotics():
    """Get antibiotic names."""
    return ANTIBIOTICS


@router.get("/resources/variant/rejection", tags=DEFAULT_TAGS)
async def get_variant_rejection():
    """Get antibiotic names."""
    return {}