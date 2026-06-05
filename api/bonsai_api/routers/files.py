"""For serving and requesting files."""

from typing import Annotated
from pathlib import Path

from fastapi import APIRouter, HTTPException, Header, status

from bonsai_api.config import settings
from bonsai_api.io import resolve_resource_path
from bonsai_api.exceptions import GenomeResourceError, InvalidRangeError, RangeOutOfBoundsError
from bonsai_api.services.files_service import build_file_response
from bonsai_api.models.enums import FileSources

from .tags import RouterTags

router = APIRouter(tags=[RouterTags.FILES])


FILE_ROOTS: dict[FileSources, Path] = {
    FileSources.REFERENCE_GENOMES: Path(settings.reference_genomes_dir),
    FileSources.GENOMIC_RESOURCES: Path(settings.annotations_dir),
}


@router.get("/files/{source}/{path:path}", name="file-resource")
async def get_file(
    source: FileSources,
    path: str,
    range: Annotated[str | None, Header()] = None,
):
    base_path = FILE_ROOTS.get(source)
    if not base_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file source: {source}",
        )

    try:
        file_path = resolve_resource_path(path, base_path)

        return build_file_response(file_path, range_header=range)

    except GenomeResourceError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    except InvalidRangeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    except RangeOutOfBoundsError as e:
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail=str(e),
        ) from e