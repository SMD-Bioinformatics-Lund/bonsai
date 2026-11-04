"""External annotation paths require an explicit opt-in for registration and serving."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from bonsai_api import doctor
from bonsai_api.config import Settings, settings
from bonsai_api.exceptions import GenomeResourceError
from bonsai_api.io import resolve_resource_path, to_relative_resource
from bonsai_api.models.enums import FileSources
from bonsai_api.models.genomic_resource import GenomicResourceCreate
from bonsai_api.routers import files
from bonsai_api.services import genomic_resource_service


@pytest.fixture
def annotation_files(tmp_path, monkeypatch):
    root = tmp_path / "annotations"
    root.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    for directory in (root, external):
        (directory / "reads.bam").write_bytes(b"alignment")
        (directory / "reads.bam.bai").write_bytes(b"index")
    monkeypatch.setattr(settings, "annotations_dir", str(root))
    monkeypatch.setattr(settings, "allow_external_annotation_paths", False)
    monkeypatch.setitem(files.FILE_ROOTS, FileSources.GENOMIC_RESOURCES, root)
    monkeypatch.setitem(files.FILE_ROOTS, FileSources.REFERENCE_GENOMES, root)
    return root, external


@pytest.mark.asyncio
@pytest.mark.parametrize("allow_external", [False, True])
@pytest.mark.parametrize("external_field", [None, "path", "index_path"])
async def test_annotation_registration_and_serving(
    annotation_files, monkeypatch, allow_external, external_field
):
    root, external = annotation_files
    monkeypatch.setattr(settings, "allow_external_annotation_paths", allow_external)
    monkeypatch.setattr(
        genomic_resource_service, "sample_exists", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        genomic_resource_service, "sample_has_resource", AsyncMock(return_value=False)
    )
    genome_id = "01a0c39b-9440-7ce2-8188-08d85f0c5ecb"
    monkeypatch.setattr(
        genomic_resource_service,
        "get_reference_genome_service",
        AsyncMock(return_value=SimpleNamespace(id=genome_id)),
    )
    insert = AsyncMock()
    monkeypatch.setattr(genomic_resource_service, "insert_genomic_resource", insert)
    paths = {"path": root / "reads.bam", "index_path": root / "reads.bam.bai"}
    if external_field:
        paths[external_field] = external / paths[external_field].name
    resource = GenomicResourceCreate.model_validate(
        {
            "reference_genome_id": genome_id,
            "pipeline_run_id": "run-1",
            "resource_data": [
                {
                    "name": "Read coverage",
                    "format": "bam",
                    "type": "alignment",
                    **{key: str(path) for key, path in paths.items()},
                }
            ],
        }
    )
    app = FastAPI()
    app.include_router(files.router)
    request = Request(
        {
            "type": "http",
            "scheme": "http",
            "server": ("testserver", 80),
            "path": "/",
            "root_path": "",
            "headers": [],
            "router": app.router,
        }
    )

    async def register():
        return await genomic_resource_service.create_genomic_resource_service(
            SimpleNamespace(),
            sample_id="01a0c3a1-1111-7000-9000-aaaaaaaaaaaa",
            request=request,
            resource=resource,
            ctx=SimpleNamespace(),
        )

    if external_field and not allow_external:
        with pytest.raises(GenomeResourceError, match="Outside allowed directory"):
            await register()
        insert.assert_not_awaited()
        return

    responses = await register()
    stored = insert.await_args.kwargs["resource_data"][0]
    with TestClient(app) as client:
        for key, url_key in (("path", "url"), ("index_path", "index_url")):
            expected = str(paths[key]) if key == external_field else paths[key].name
            assert stored[key] == expected
            url = getattr(responses[0], url_key)
            assert "//" not in url.removeprefix("http://")
            response = client.get(url)
            assert response.status_code == 200
            assert response.content == paths[key].read_bytes()
            # Restoring the restriction blocks previously registered external files.
            if key == external_field:
                monkeypatch.setattr(settings, "allow_external_annotation_paths", False)
                assert client.get(url).status_code == 404
                monkeypatch.setattr(settings, "allow_external_annotation_paths", True)
        # The opt-in never changes reference genome file restrictions.
        assert (
            client.get(f"/files/reference-genomes/{external / 'reads.bam'}").status_code
            == 404
        )


@pytest.mark.parametrize("resource", ["../external/reads.bam", ""])
def test_external_opt_in_keeps_identifier_validation(annotation_files, resource):
    root, _ = annotation_files
    with pytest.raises(GenomeResourceError):
        resolve_resource_path(resource, root, allow_external_paths=True)


def test_external_opt_in_still_requires_existing_readable_files(
    annotation_files, monkeypatch
):
    root, external = annotation_files
    with pytest.raises(GenomeResourceError, match=r"\.\."):
        to_relative_resource(
            str(external / ".." / "external" / "reads.bam"),
            root,
            allow_external_paths=True,
        )
    with pytest.raises(GenomeResourceError, match="not found"):
        to_relative_resource(
            str(external / "missing.bam"), root, allow_external_paths=True
        )
    monkeypatch.setattr("bonsai_api.io.os.access", lambda *args: False)
    with pytest.raises(GenomeResourceError, match="not readable"):
        to_relative_resource(
            str(external / "reads.bam"), root, allow_external_paths=True
        )


def test_doctor_respects_external_annotation_setting(annotation_files, monkeypatch):
    _, external = annotation_files
    sample = {
        "genomic_resources": [
            {
                "type": "alignment",
                "path": str(external / "reads.bam"),
                "index_path": str(external / "reads.bam.bai"),
            }
        ]
    }
    assert len(doctor.check_alignment(sample)) == 2
    monkeypatch.setattr(settings, "allow_external_annotation_paths", True)
    assert doctor.check_alignment(sample) == []


def test_external_annotation_paths_are_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ALLOW_EXTERNAL_ANNOTATION_PATHS", raising=False)
    assert Settings().allow_external_annotation_paths is False
    monkeypatch.setenv("ALLOW_EXTERNAL_ANNOTATION_PATHS", "true")
    assert Settings().allow_external_annotation_paths is True
