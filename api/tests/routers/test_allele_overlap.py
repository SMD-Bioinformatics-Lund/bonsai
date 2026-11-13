"""No-overlap requests fail before a clustering job can be queued."""

from types import SimpleNamespace
from unittest.mock import Mock

import mongomock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bonsai_api.dependencies import get_database
from bonsai_api.internal.error_handlers import register_exception_handlers
from bonsai_api.redis.models import SubmittedJob
from bonsai_api.routers import cluster as routes


@pytest.mark.parametrize("method", ["mlst", "cgmlst"])
@pytest.mark.parametrize("overlap", [False, True])
def test_route_requires_overlap_with_real_profile_selection(
    monkeypatch, method, overlap
):
    collection = mongomock.MongoClient().db.samples
    for sid, calls in [
        ("a", {"x": "1", "y": "LNF"}),
        ("b", {"x": "1" if overlap else "LNF", "y": "2"}),
    ]:
        collection.insert_one(
            {
                "sample_id": sid,
                "typing_result": [
                    {
                        "software": "mlst" if method == "mlst" else "chewbbaca",
                        "analysis_type": method,
                        "status": "parsed",
                        "result": {"scheme": "same", "alleles": calls},
                    }
                ],
            }
        )

    async def records(rows):
        for row in rows:
            yield row

    async def aggregate(pipeline):
        return records(
            list(collection.aggregate([s for s in pipeline if "$unset" not in s]))
        )

    db = SimpleNamespace(sample_collection=SimpleNamespace(aggregate=aggregate))
    app = FastAPI()
    app.include_router(routes.router)
    register_exception_handlers(app)
    app.dependency_overrides[get_database] = lambda: db
    enqueue = Mock(return_value=SubmittedJob(id="job", task="cluster"))
    monkeypatch.setattr(routes, "schedule_allele_cluster_samples", enqueue)
    response = TestClient(app).post(
        f"/cluster/{method}", json={"sampleIds": ["a", "b"], "method": "MSTreeV2"}
    )
    if overlap:
        assert response.status_code == 201
        enqueue.assert_called_once()
    else:
        assert response.status_code == 422
        assert "no jointly called loci" in response.json()["detail"]
        enqueue.assert_not_called()
