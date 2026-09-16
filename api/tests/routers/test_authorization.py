"""Authorization coverage for sensitive API routes."""

import inspect

import pytest
from bonsai_api.config import settings
from bonsai_api.dependencies import get_current_active_user
from bonsai_api.routers import analysis, cluster, jobs
from bonsai_api.routers.samples import sample_analysis, samples
from fastapi import FastAPI
from fastapi.params import Security as SecurityParam
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    "handler, parameter, expected_scope",
    [
        (cluster.cluster_samples, "current_user", "samples:read"),
        (cluster.index_genome_signatures, "current_user", "samples:write"),
        (jobs.check_job_status, "current_user", "samples:read"),
        (jobs.get_report_from_minhash, "current_user", "samples:write"),
        (
            sample_analysis.create_genome_signatures_sample,
            "current_user",
            "samples:write",
        ),
        (sample_analysis.add_ska_index_to_sample, "current_user", "samples:write"),
        (analysis.upload_analysis, "user", "samples:write"),
        (analysis.create_analysis_curation, "user", "samples:update"),
        (analysis.list_curations, "user", "samples:read"),
        (analysis.get_curation, "user", "samples:read"),
        (analysis.approve_curation, "user", "samples:update"),
        (analysis.delete_curation, "user", "samples:update"),
        (samples.delete_many_samples, "current_user", "samples:write"),
        (samples.delete_sample, "current_user", "samples:write"),
    ],
)
def test_sensitive_route_uses_expected_security_scope(
    handler, parameter, expected_scope
):
    """Every sensitive handler declares the intended authorization scope."""
    dependency = inspect.signature(handler).parameters[parameter].default

    assert isinstance(dependency, SecurityParam)
    assert dependency.dependency is get_current_active_user
    assert dependency.scopes == [expected_scope]


def test_job_status_rejects_anonymous_requests(monkeypatch):
    """A protected route rejects a request before its handler is executed."""
    monkeypatch.setattr(settings, "api_authentication", True)
    test_app = FastAPI()
    test_app.include_router(jobs.router)

    with TestClient(test_app) as client:
        response = client.get("/job/status/untrusted-job-id")

    assert response.status_code == 401
