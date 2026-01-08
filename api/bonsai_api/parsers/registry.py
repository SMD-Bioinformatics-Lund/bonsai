"""Simple parser registry for analysis files (placeholder).

This is a minimal implementation used by the API while a full parser
registry / schema system is developed. Parsers are keyed by (analysis_type,
software) and may inspect a software_version if needed.
"""

import json
import logging
from typing import Callable, Any
from fastapi import HTTPException
from fastapi import UploadFile

LOG = logging.getLogger(__name__)

Parser = Callable[[UploadFile], Any]


async def _json_parser(file: UploadFile) -> Any:
    head = await file.read(2)
    await file.seek(0)
    raw = await file.read()
    await file.close()
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception as exc:  # pragma: no cover - defensive
        LOG.exception("Failed to parse JSON file")
        raise HTTPException(400, "File is not valid JSON") from exc


# registry can be extended to register specific parsers keyed by (analysis_type, software)
_REGISTRY: dict[tuple[str, str], Parser] = {}


def register_parser(analysis_type: str, software: str, parser: Parser) -> None:
    _REGISTRY[(analysis_type, software)] = parser


def get_parser(analysis_type: str, software: str, software_version: str | None = None) -> Parser:
    """Return a parser function for the requested analysis/software.

    Falls back to a generic JSON parser if no specific parser is registered.
    Raise HTTPException(400) if file can't be parsed.
    """
    parser = _REGISTRY.get((analysis_type, software))
    if parser:
        return parser
    # fallback to JSON parser
    return _json_parser
