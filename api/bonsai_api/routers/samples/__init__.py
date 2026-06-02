"""Sample routes organized by domain responsibility."""

from fastapi import APIRouter

from . import sample_analysis, sample_metadata, sample_qc, samples, search
from bonsai_api.routers.tags import RouterTags

router = APIRouter()

# Register all routers
router.include_router(samples.router, tags=[RouterTags.SAMPLE])
router.include_router(sample_analysis.router, tags=[RouterTags.SAMPLE, RouterTags.FILES])
router.include_router(sample_qc.router, tags=[RouterTags.SAMPLE, RouterTags.QUALITY])
router.include_router(search.router, tags=[RouterTags.SAMPLE, RouterTags.SEARCH])
router.include_router(sample_metadata.router, tags=[RouterTags.SAMPLE, RouterTags.META])

__all__ = ["router"]
