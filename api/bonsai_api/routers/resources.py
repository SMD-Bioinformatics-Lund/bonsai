"""Public resources and constants."""

import logging
import pathlib
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Query, status
from fastapi.responses import FileResponse

from api.bonsai_api.routers.shared import RouterTags
from bonsai_api.config import settings
from bonsai_api.io import (
    InvalidRangeError,
    RangeOutOfBoundsError,
    is_file_readable,
    send_partial_file,
)
from bonsai_models.models.antibiotics import ANTIBIOTICS
from bonsai_models.models.qc import VARIANT_REJECTION_REASONS

LOG = logging.getLogger(__name__)
router = APIRouter()

READ_PERMISSION = "resources:read"


@router.get("/resources/antibiotics", tags=[RouterTags.ASSET])
async def get_antibiotics():
    """Get antibiotic names."""
    return ANTIBIOTICS


@router.get("/resources/variant/rejection", tags=[RouterTags.ASSET])
async def get_variant_rejection():
    """Get antibiotic names."""
    return VARIANT_REJECTION_REASONS


@router.get("/resources/genome/info", tags=[RouterTags.ASSET])
async def get_genome_resources(
    file: str = Query(..., description="Name of the annotation file with suffix"),
    range: Annotated[str | None, Header()] = None,
) -> str:
    """Genome sequence and annotated genes for a given reference genome."""
    base_path = pathlib.Path(settings.reference_genomes_dir)

    # generate file path
    file_path = base_path.joinpath(file)

    # check if resource exist
    try:
        is_file_readable(str(file_path))
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Annotation {file} not found.",
        )
    except PermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error occured reading {file}.",
        )

    # send file if byte range is not set
    if range is None:
        response = FileResponse(file_path, filename=file_path.name)
    else:
        try:
            response = send_partial_file(file_path, range)
        except InvalidRangeError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            ) from error
        except RangeOutOfBoundsError as error:
            raise HTTPException(
                status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
                detail=str(error),
            ) from error
    return response
