import mimetypes
from pathlib import Path
from fastapi import Response

from bonsai_api.io import send_partial_file

def build_file_response(path: Path, range_header: str | None) -> Response:
    """Return a full or partial file response based on range header."""

    if range_header is None:
        return Response(
            content=path.read_bytes(),
            media_type=mimetypes.guess_type(path)[0],
            headers={"Accept-Ranges": "bytes"},
        )

    return send_partial_file(path, range_header)