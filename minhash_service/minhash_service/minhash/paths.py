"""Get paths to different resources."""

from pathlib import Path

from minhash_service.config import settings


def ensure_file_exists(path: Path) -> Path:
    """Assert that file exists."""
    if not path.is_file():
        raise FileNotFoundError(f"File {path} is not found.")
    return path


def get_signature_files(signature_dir: Path, suffix: str = ".sig") -> list[Path]:
    """Get uploaded signatures."""
    files = signature_dir.glob(f"*{suffix}")
    return files


def get_signature_path(
    sample_id: str, suffix=".sig", ensure_exists: bool = True
) -> Path:
    """Get path to a sample signature file."""
    path = settings.signature_dir / f"{sample_id}{suffix}"
    return ensure_file_exists(path) if ensure_exists else path


def get_index_path(ensure_exists: bool = True) -> Path:
    """Get path to sourmash index.

    Index type will be encoded in index name."""
    file_name = f"{settings.index_name}.{settings.db_format.name.lower()}.idx"
    path = settings.signature_dir / file_name
    return ensure_file_exists(path) if ensure_exists else path
