"""Read-only, batched checks executed where SKA files are mounted."""

import os
from pathlib import Path

from .config import settings


def check_samples(samples: list[dict]) -> dict:
    """Check SKA availability using the same filename fallback as clustering."""
    findings = []
    by_name = None
    for sample in samples:
        name = sample["ska_index"]
        path = Path(settings.index_dir) / name
        try:
            if not path.is_file():
                if by_name is None:
                    found = {}

                    def walk_error(error):
                        raise error

                    for root, _, files in os.walk(
                        settings.index_dir, onerror=walk_error
                    ):
                        for filename in files:
                            found.setdefault(filename, []).append(Path(root) / filename)
                    by_name = found
                matches = {
                    candidate.resolve()
                    for candidate in by_name.get(path.name, [])
                    if candidate.is_file()
                }
                if len(matches) > 1:
                    raise ValueError(
                        f"Multiple SKA index files match {path.name!r}; "
                        "provide an exact accessible path."
                    )
                if matches:
                    path = next(iter(matches))
            if not path.is_file():
                message = "SKA index file is missing"
            elif not os.access(path, os.R_OK):
                message = "SKA index file is unreadable"
            elif path.stat().st_size == 0:
                message = "SKA index file is empty"
            else:
                continue
        except (OSError, ValueError) as error:
            message = f"Cannot access SKA index: {error}"
        findings.append(
            {
                "sample_id": sample["sample_id"],
                "file_type": "ska",
                "message": message,
                "path": str(path),
            }
        )
    return {"findings": findings, "errors": []}
