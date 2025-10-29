"""Parser registry and logic."""

from collections import defaultdict
from packaging.version import Version

from .models.base import ParserFunc


_PARSER_REGISTRY: dict[str, list[tuple[Version, Version, ParserFunc]]] = defaultdict(list)

UNBOUNDED_VERSION = "99999.99999"

def register_parser(tool: str, min_version: str, max_version: str = UNBOUNDED_VERSION):
    def _decorator(fn: ParserFunc):
        _PARSER_REGISTRY[tool].append((Version(min_version), Version(max_version), fn))
        return fn
    return _decorator


def get_parser(tool: str, version: str) -> ParserFunc:
    """Return parser function for tool and version.
    
    Raises NotImplementedError if no matching parser is found."""
    version_obj = Version(version)
    for min_v, max_v, parser in _PARSER_REGISTRY.get(tool, []):
        if min_v <= version_obj <= max_v:
            return parser
    raise NotImplementedError(f"No parser registered for {tool} version {version}")
