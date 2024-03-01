"""Public resources and constants."""

import logging
import os
import pathlib
from enum import Enum
from typing import Annotated

from app.config import REFERENCE_GENOMES_DIR
from app.io import InvalidRangeError, RangeOutOfBoundsError, send_partial_file, is_file_readable
from fastapi import APIRouter, Header, HTTPException, Path, Query, status
from fastapi.responses import FileResponse, Response

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


class AnnotationType(Enum):
    FASTA = "fasta"
    FASTA_INDEX = "fasta_index"
    GFF = "gff"


@router.get("/resources/genome/{accession_no}/download", tags=DEFAULT_TAGS)
async def get_genome_resources(
    accession_no: str = Path(..., title="Genome accession number", min_length=3),
    annotation_type: AnnotationType = Query(...),
    range: Annotated[str | None, Header()] = None,
) -> str:
    """Get resources for reference genome."""
    base_path = pathlib.Path(REFERENCE_GENOMES_DIR)
    match annotation_type:
        case AnnotationType.FASTA:
            suffix = ".fasta"
        case AnnotationType.FASTA_INDEX:
            suffix = ".fasta.fai"
        case AnnotationType.GFF:
            suffix = ".gff"

    # generate file path
    file_path = base_path.joinpath(f"{accession_no}{suffix}")

    # check if resource exist
    if not is_file_readable(str(file_path)):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error occured reading {accession_no} data",
        )

    # send file if byte range is not set
    if range is None:
        response = FileResponse(file_path)
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
