"""Test CLI tasks"""
from types import SimpleNamespace

import pytest

from bonsai_api.cli import cli_tasks


class DummyAsyncCM:
    """Dummy async context manager for testing."""
    def __init__(self, value):
        self._value = value

    async def __aenter__(self):
        return self._value

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_run_lims_export_success(monkeypatch):
    # Arrange: patch get_db_connection and get_sample, and export helpers
    monkeypatch.setattr(cli_tasks, "get_db_connection", lambda: DummyAsyncCM(None))

    sample = SimpleNamespace(pipeline=SimpleNamespace(assay="A1"))

    async def fake_get_sample(db, sample_id):
        return sample

    monkeypatch.setattr(cli_tasks, "get_sample", fake_get_sample)

    # config object list with matching assay
    monkeypatch.setattr(cli_tasks, "load_export_config", lambda path: [SimpleNamespace(assay="A1")])
    monkeypatch.setattr(cli_tasks, "lims_rs_formatter", lambda s, c: {"rows": [["a"]]})
    monkeypatch.setattr(cli_tasks, "serialize_lims_results", lambda data, delimiter: "a,b\n")

    # Act
    out = await cli_tasks.run_lims_export("S1", None, "csv")

    # Assert
    assert out == "a,b\n"


@pytest.mark.asyncio
async def test_run_lims_export_no_config(monkeypatch):
    monkeypatch.setattr(cli_tasks, "get_db_connection", lambda: DummyAsyncCM(None))
    sample = SimpleNamespace(pipeline=SimpleNamespace(assay="B2"))

    async def fake_get_sample(db, sample_id):
        return sample

    monkeypatch.setattr(cli_tasks, "get_sample", fake_get_sample)
    monkeypatch.setattr(cli_tasks, "load_export_config", lambda path: [])

    with pytest.raises(ValueError):
        await cli_tasks.run_lims_export("S1", None, "csv")


@pytest.mark.asyncio
async def test_run_check_paths_no_missing(monkeypatch):
    # patch get_db_connection and get_samples
    monkeypatch.setattr(cli_tasks, "get_db_connection", lambda: DummyAsyncCM(None))

    # make get_samples return an object with .data and .records_filtered
    async def fake_get_samples(db):
        return SimpleNamespace(data=[SimpleNamespace(sample_id="s1")], records_filtered=1)

    monkeypatch.setattr(cli_tasks, "get_samples", fake_get_samples)

    # patch verify functions to return no missing files
    monkeypatch.setattr(cli_tasks.verify, "verify_reference_genome", lambda s: [])
    monkeypatch.setattr(cli_tasks.verify, "verify_read_mapping", lambda s: None)
    monkeypatch.setattr(cli_tasks.verify, "verify_ska_index", lambda s, timeout=60: None)
    monkeypatch.setattr(cli_tasks.verify, "verify_sourmash_files", lambda s, timeout=60: None)

    # Test that the different verify functions are called and no missing files are found
    res = await cli_tasks.run_check_paths(10)
    assert res["records_filtered"] == 1
    assert isinstance(res["report"], str)
    assert res["missing_files"] == []


@pytest.mark.asyncio
async def test_run_check_paths_with_missing(monkeypatch):
    """Test that missing files are reported when encountered by the verify functions."""
    monkeypatch.setattr(cli_tasks, "get_db_connection", lambda: DummyAsyncCM(None))

    sample_obj = SimpleNamespace(sample_id="s2")

    async def fake_get_samples(db):
        return SimpleNamespace(data=[sample_obj], records_filtered=1)

    monkeypatch.setattr(cli_tasks, "get_samples", fake_get_samples)

    # create a MissingFile instance
    mf = cli_tasks.MissingFile(sample_id="s2", file_type="read_mapping", error_type="FileNotFound", path="/tmp/x")

    monkeypatch.setattr(cli_tasks.verify, "verify_reference_genome", lambda s: [])
    monkeypatch.setattr(cli_tasks.verify, "verify_read_mapping", lambda s: mf)
    monkeypatch.setattr(cli_tasks.verify, "verify_ska_index", lambda s, timeout=60: None)
    monkeypatch.setattr(cli_tasks.verify, "verify_sourmash_files", lambda s, timeout=60: None)

    res = await cli_tasks.run_check_paths(10)
    assert res["records_filtered"] == 1
    assert len(res["missing_files"]) == 1
    assert "s2" in res["report"]
