"""File IO operations."""

import logging
import mimetypes
import os
import pathlib
import re
from enum import StrEnum
from io import StringIO
from pathlib import Path

import pandas as pd
from fastapi.responses import Response

from .models.metadata import InputTableMetadata, TableMetadataInDb
from .exceptions import GenomeResourceError, InvalidRangeError, RangeOutOfBoundsError

LOG = logging.getLogger(__name__)
BYTE_RANGE_RE = re.compile(r"bytes=(\d+)-(\d+)?$")

TARGETED_ANTIBIOTICS = {
    "rifampicin": {"abbrev": "rif", "split_res_level": False},
    "isoniazid": {"abbrev": "inh", "split_res_level": True},
    "pyrazinamide": {"abbrev": "pyr", "split_res_level": False},
    "ethambutol": {"abbrev": "etb", "split_res_level": False},
    "amikacin": {"abbrev": "ami", "split_res_level": False},
    "levofloxacin": {"abbrev": "lev", "split_res_level": False},
}


class TBResponses(StrEnum):
    """Valid responses for M. tuberculosis results."""

    resistant = "Mutation pavisad"
    susceptible = "Mutation ej pavisad"
    sample_failed = "Ej bedombart"


def is_file_readable(file_path: str) -> bool:
    """Check if file exist and is readable.

    :param file_path: File path object
    :type file_path: str
    :return: True if readable and exist
    :rtype: bool
    """
    path = pathlib.Path(file_path)
    if not path.is_file():
        LOG.debug("trying to access missing reference genome data: %s", file_path)
        raise FileNotFoundError(file_path)

    if not os.access(path, os.R_OK):
        LOG.debug("file: %s cant read by the system user", file_path)
        raise PermissionError(file_path)

    return True


def parse_byte_range(byte_range: str) -> tuple[int, int]:
    """Returns the two numbers in 'bytes=123-456' or throws ValueError.
    The last number or both numbers may be None.
    """
    if byte_range.strip() == "":
        return None, None

    m = BYTE_RANGE_RE.match(byte_range)
    if not m:
        raise InvalidRangeError(f"Invalid byte range {byte_range}")

    first, last = [x and int(x) for x in m.groups()]
    if last and last < first:
        raise InvalidRangeError(f"Invalid byte range {byte_range}")
    return first, last


def send_partial_file(path: Path, range_header: str) -> Response:
    """Send partial file as a response.

    :param path: File path
    :type path: Path
    :param range_header: byte range, ie bytes=123-456
    :type range_header: str
    :raises RangeOutOfBoundsError: Error if the byte range is out of bounds.
    :return: Exception
    :rtype: Response
    """
    byte_range = parse_byte_range(range_header)
    first, last = byte_range

    data = None
    with path.open("rb") as file_handle:
        fs = os.fstat(file_handle.fileno())
        file_len = fs[6]
        if first >= file_len:
            raise RangeOutOfBoundsError("Requested Range Not Satisfiable")

        if last is None or last >= file_len:
            last = file_len - 1
        response_length = last - first + 1

        file_handle.seek(first)
        data = file_handle.read(response_length)

    response_headers = {
        "Content-type": "application/octet-stream",
        "Accept-Ranges": "bytes",
        "Content-Range": f"bytes {first}-{last}/{file_len}",
        "Content-Length": str(response_length),
    }
    return Response(
        content=data,
        status_code=206,
        media_type=mimetypes.guess_type(path)[0],
        headers=response_headers,
    )


def parse_metadata_table(
    entry: InputTableMetadata, index_col: int | None = None
) -> TableMetadataInDb:
    """Parse a stringified csv file as a mongo representation of a table."""
    df = pd.read_csv(StringIO(entry.value), sep=",", index_col=index_col)
    df_json = df.to_dict(orient="split", index=False if index_col is None else True)
    return TableMetadataInDb.model_validate(
        {"fieldname": entry.fieldname, "category": entry.category, **df_json}
    )


def validate_resource_identifier(resource: str) -> Path:
    """Validate a genome resource identifier to prevent path traversal and ensure it is not empty."""

    if not resource:
        raise GenomeResourceError("Empty genome resource identifier")

    requested = Path(resource)

    if requested.is_absolute() or ".." in requested.parts:
        raise GenomeResourceError("Invalid genome resource identifier")

    return requested



def resolve_resource_path(resource: str, base_dir: Path) -> Path:
    """Resolve and validate a resource path."""

    base_dir = base_dir.resolve()
    requested = validate_resource_identifier(resource)
    resolved = (base_dir / requested).resolve()

    if base_dir not in resolved.parents:
        raise GenomeResourceError("Outside allowed directory")

    if not resolved.is_file():
        raise GenomeResourceError(f"{resolved} not found")

    if not os.access(resolved, os.R_OK):
        raise GenomeResourceError(f"{resolved} not readable")

    return resolved


def to_relative_resource(resource: str | None, base_dir: Path) -> str | None:
    """Convert an absolute resource path to a relative one, validating it in the process."""

    if not resource:
        return None
    return str(resolve_resource_path(resource, base_dir).relative_to(base_dir))
