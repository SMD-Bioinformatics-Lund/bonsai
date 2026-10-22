"""Doctor follows worker path resolution without loading SKA indexes."""

from ska_service import doctor


def test_nested_host_path_fallback_and_missing_empty_indexes(tmp_path, monkeypatch):
    monkeypatch.setattr(doctor.settings, "index_dir", str(tmp_path))
    folder = tmp_path / "nested"
    folder.mkdir()
    (folder / "present.skf").write_bytes(b"index")
    (folder / "empty.skf").touch()
    samples = [
        {"sample_id": name, "ska_index": f"/original/host/{name}.skf"}
        for name in ("present", "empty", "missing")
    ]
    result = doctor.check_samples(samples)
    assert {f["sample_id"] for f in result["findings"]} == {"empty", "missing"}
    assert not result["errors"]
