from pathlib import Path

from minhash_service.utils import ensure_directory_structure


def test_ensure_directory_structure(tmp_path: Path):
    """Test that the directory structure is created."""

    path = tmp_path / "foo" / "bar"

    ensure_directory_structure(path)

    assert path.is_dir()
