"""Utility functions."""

from pathlib import Path

def ensure_directory_structure(val: Path) -> Path:
    """Create the directory structure for the provided path, including any necessary parent directories."""
    val.mkdir(parents=True, exist_ok=True)
    return val
