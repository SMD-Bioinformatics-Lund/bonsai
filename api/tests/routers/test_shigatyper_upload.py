"""The multipart route forwards an optional ShigaTyper companion file."""

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bonsai_api.routers import analysis


@pytest.mark.parametrize("with_hits", [False, True])
def test_upload_route_forwards_shigatyper_files(monkeypatch, with_hits):
    captured = {}

    async def ingest(_db, **kwargs):
        captured["report"] = await kwargs["file"].read()
        captured["hits"] = await kwargs["hits_file"].read() if kwargs["hits_file"] else None
        return {"analysis_id": "analysis-1"}

    service = AsyncMock(side_effect=ingest)
    monkeypatch.setattr(analysis, "ingest_analysis_service", service)
    app = FastAPI()
    app.include_router(analysis.router)
    for dependency in (
        analysis.get_database,
        analysis.get_current_active_user,
        analysis.get_request_context,
        analysis.get_audit_log,
    ):
        app.dependency_overrides[dependency] = lambda: None

    report = b"sample\tprediction\tipaB\tnotes\ns1\tEIEC\t+\t\n"
    hits = b"Hit\tNumber of reads\nipaH_c\t331\n"
    files = {"file": ("s1.tsv", report, "text/tab-separated-values")}
    if with_hits:
        files["hits_file"] = ("s1-hits.tsv", hits, "text/tab-separated-values")
    with TestClient(app) as client:
        response = client.post(
            "/analysis/",
            data={
                "sample_id": "sample-1",
                "software": "shigatyper",
                "software_version": "2.0.5",
            },
            files=files,
        )
    assert response.status_code == 201
    assert response.json() == {"analysis_id": "analysis-1"}
    assert captured == {"report": report, "hits": hits if with_hits else None}
    service.assert_awaited_once()
