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


def test_doctor_reports_ambiguous_filename_recovery(tmp_path, monkeypatch):
    monkeypatch.setattr(doctor.settings, "index_dir", str(tmp_path))
    for run in ("run-1", "run-2"):
        folder = tmp_path / run
        folder.mkdir()
        (folder / "sample.skf").write_bytes(b"index")
    result = doctor.check_samples(
        [
            {"sample_id": "sample", "ska_index": "/unmounted/run-2/sample.skf"},
            {"sample_id": "exact", "ska_index": str(tmp_path / "run-2/sample.skf")},
        ]
    )
    assert len(result["findings"]) == 1
    assert result["findings"][0]["sample_id"] == "sample"
    assert "Multiple SKA index files" in result["findings"][0]["message"]


def test_doctor_does_not_reuse_an_incomplete_directory_scan(tmp_path, monkeypatch):
    monkeypatch.setattr(doctor.settings, "index_dir", str(tmp_path))
    (tmp_path / "sample.skf").write_bytes(b"index")

    def incomplete_walk(root, onerror=None):
        yield str(tmp_path), [], ["sample.skf"]
        onerror(PermissionError("Cannot scan one sequencing run"))

    monkeypatch.setattr(doctor.os, "walk", incomplete_walk)
    result = doctor.check_samples(
        [
            {"sample_id": sid, "ska_index": "/unmounted/sample.skf"}
            for sid in ("first", "second")
        ]
    )
    assert {finding["sample_id"] for finding in result["findings"]} == {
        "first",
        "second",
    }
    assert all("Cannot scan" in finding["message"] for finding in result["findings"])
