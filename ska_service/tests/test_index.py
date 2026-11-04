"""Filename recovery must not select a file from an arbitrary sequencing run."""

from types import SimpleNamespace

import pytest

from ska_service.ska.index import resolve_index_path
from ska_service.ska import index


def test_exact_path_is_used_even_when_other_files_share_the_name(tmp_path):
    for run in ("run-1", "run-2"):
        (tmp_path / run).mkdir()
        (tmp_path / run / "sample.skf").touch()
    expected = tmp_path / "run-2" / "sample.skf"
    assert (
        resolve_index_path(
            str(expected), SimpleNamespace(index_dir=tmp_path), find_missing=True
        )
        == expected
    )


def test_recovery_requires_a_unique_basename(tmp_path):
    for run in ("run-1", "run-2"):
        (tmp_path / run).mkdir()
        (tmp_path / run / "sample.skf").touch()
    with pytest.raises(ValueError, match="Multiple SKA index files"):
        resolve_index_path(
            "/unmounted/run-2/sample.skf",
            SimpleNamespace(index_dir=tmp_path),
            find_missing=True,
        )


def test_unique_recovery_and_missing_file(tmp_path):
    folder = tmp_path / "nested"
    folder.mkdir()
    expected = folder / "sample.skf"
    expected.touch()
    settings = SimpleNamespace(index_dir=tmp_path)
    assert (
        resolve_index_path("/unmounted/sample.skf", settings, find_missing=True)
        == expected
    )
    with pytest.raises(FileNotFoundError):
        resolve_index_path("missing.skf", settings, find_missing=True)


def test_recovery_can_be_disabled(tmp_path):
    (tmp_path / "sample.skf").touch()
    with pytest.raises(FileNotFoundError):
        resolve_index_path("/unmounted/sample.skf", SimpleNamespace(index_dir=tmp_path))


def test_recovery_rejects_an_incomplete_directory_scan(tmp_path, monkeypatch):
    (tmp_path / "sample.skf").touch()

    def incomplete_walk(root, onerror=None):
        yield str(tmp_path), [], ["sample.skf"]
        if onerror:
            onerror(PermissionError("Cannot scan one sequencing run"))

    monkeypatch.setattr(index.os, "walk", incomplete_walk)
    with pytest.raises(PermissionError, match="Cannot scan"):
        resolve_index_path(
            "/unmounted/sample.skf",
            SimpleNamespace(index_dir=tmp_path),
            find_missing=True,
        )
