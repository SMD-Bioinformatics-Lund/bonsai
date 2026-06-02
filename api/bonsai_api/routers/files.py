"""For serving and requesting files."""

from typing import Annotated
from pathlib import Path

from fastapi import APIRouter, HTTPException, Header, status

from bonsai_api.config import settings
from bonsai_api.io import resolve_resource_path
from bonsai_api.exceptions import GenomeResourceError, InvalidRangeError, RangeOutOfBoundsError
from bonsai_api.services.files_service import build_file_response

from .tags import RouterTags

router = APIRouter(tags=[RouterTags.FILES])


@router.get("/files/{path:path}", name="file-resource")
async def get_file(
    path: str,
    range: Annotated[str | None, Header()] = None,
):
    base_path = Path(settings.reference_genomes_dir)

    try:
        file_path = resolve_resource_path(path, base_path)

        return build_file_response(file_path, range)

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