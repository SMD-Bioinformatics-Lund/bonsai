from pathlib import Path

def get_data_path(data_dir: Path, file_name: str) -> Path:
    """Helper to get full path to a test data file."""
    file_path = data_dir / file_name
    if not file_path.exists():
        raise FileNotFoundError(f"File '{file_path}' not found in test data directory.")
    return file_path