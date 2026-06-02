"""Sample routes organized by domain responsibility."""

from fastapi import APIRouter

from bonsai_api.routers.tags import RouterTags
from . import sample_analysis, sample_metadata, sample_qc, samples, genomic_resources
from .permissions import READ_PERMISSION, WRITE_PERMISSION, UPDATE_PERMISSION

router = APIRouter()

# Register all routers
router.include_router(samples.router, tags=[RouterTags.SAMPLE])
router.include_router(
    sample_analysis.router, tags=[RouterTags.SAMPLE, RouterTags.FILES]
)
router.include_router(sample_qc.router, tags=[RouterTags.SAMPLE, RouterTags.QUALITY])
router.include_router(sample_metadata.router, tags=[RouterTags.SAMPLE, RouterTags.META])
router.include_router(sample_metadata.router, tags=[RouterTags.SAMPLE, RouterTags.META])
router.include_router(
    genomic_resources.router, tags=[RouterTags.SAMPLE, RouterTags.GENOMIC_RESOURCE]
)

__all__ = ["router"]
