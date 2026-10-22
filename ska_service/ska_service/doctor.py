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
                    by_name = {}

                    def walk_error(error):
                        raise error

                    for root, _, files in os.walk(
                        settings.index_dir, onerror=walk_error
                    ):
                        for filename in files:
                            by_name.setdefault(filename, Path(root) / filename)
                path = by_name.get(path.name, path)
            if not path.is_file():
                message = "SKA index file is missing"
            elif not os.access(path, os.R_OK):
                message = "SKA index file is unreadable"
            elif path.stat().st_size == 0:
                message = "SKA index file is empty"
            else:
                continue
        except OSError as error:
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
