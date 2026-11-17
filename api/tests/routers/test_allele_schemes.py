"""Browser validation and authoritative submission enforce the same scheme rules."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from bonsai_api.crud.cluster import TypingProfileAggregate
from bonsai_api.dependencies import get_database
from bonsai_api.internal.error_handlers import register_exception_handlers
from bonsai_api.redis.models import SubmittedJob
from bonsai_api.routers import cluster as routes


@pytest.fixture
def endpoint(monkeypatch):
    app = FastAPI()
    app.include_router(routes.router)
    register_exception_handlers(app)
    app.dependency_overrides[get_database] = lambda: SimpleNamespace()
    getter = AsyncMock(
        return_value=[
            TypingProfileAggregate(
                sample_id=sid, scheme="same", assay="same", typing_result={"x": 1}
            )
            for sid in ["a", "b"]
        ]
    )
    schedule = Mock(return_value=SubmittedJob(id="job", task="cluster"))
    monkeypatch.setattr(routes, "get_typing_profiles", getter)
    monkeypatch.setattr(routes, "schedule_allele_cluster_samples", schedule)
    return TestClient(app), getter, schedule


@pytest.mark.parametrize("method", ["mlst", "cgmlst"])
def test_direct_submission_cannot_bypass_scheme_checks(endpoint, method):
    client, getter, schedule = endpoint
    getter.return_value[1].scheme = "other"
    response = client.post(
        f"/cluster/{method}", json={"sampleIds": ["a", "b"], "method": "MSTreeV2"}
    )
    assert response.status_code == 422
    identity = "analysis profiles" if method == "cgmlst" else "typing schemes"
    assert f"different {identity}" in response.json()["detail"]
    getter.assert_awaited_once()
    schedule.assert_not_called()


def test_static_preflight_route_checks_both_methods(endpoint):
    client, getter, schedule = endpoint
    incompatible = [
        TypingProfileAggregate(
            sample_id=sid, scheme=sid, assay="same", typing_result={"x": 1}
        )
        for sid in ["a", "b"]
    ]
    compatible = getter.return_value
    getter.side_effect = [incompatible, compatible]
    response = client.post("/cluster/validate", json={"sampleIds": ["a", "b"]})
    assert response.status_code == 200
    assert response.json()["mlst"]["can_cluster"] is False
    assert response.json()["cgmlst"]["can_cluster"] is True
    assert [call.args[-1] for call in getter.await_args_list] == ["mlst", "cgmlst"]
    schedule.assert_not_called()


@pytest.mark.parametrize("assay", [None, "other"])
def test_mlst_assay_check_applies_to_preflight_and_submission(endpoint, assay):
    client, getter, schedule = endpoint
    getter.return_value[1].assay = assay
    preflight = client.post("/cluster/validate", json={"sampleIds": ["a", "b"]})
    assert preflight.status_code == 200
    validation = preflight.json()["mlst"]
    assert validation["can_cluster"] is False
    assert "analysis profile" in validation["notice"]
    assert preflight.json()["cgmlst"]["can_cluster"] is True

    submission = client.post(
        "/cluster/mlst", json={"sampleIds": ["a", "b"], "method": "MSTreeV2"}
    )
    assert submission.status_code == 422
    assert submission.json()["detail"] == validation["notice"]
    schedule.assert_not_called()


@pytest.mark.parametrize("method", ["mlst", "cgmlst"])
def test_compatible_profiles_are_validated_from_the_same_read_as_submission(
    endpoint, method
):
    client, getter, schedule = endpoint
    response = client.post(
        f"/cluster/{method}", json={"sampleIds": ["a", "b"], "method": "MSTreeV2"}
    )
    assert response.status_code == 201
    getter.assert_awaited_once()
    assert schedule.call_args.args[0] is getter.return_value


@pytest.mark.parametrize("method", ["mlst", "cgmlst"])
def test_locus_differences_only_block_mlst_preflight_and_submission(endpoint, method):
    client, getter, schedule = endpoint
    getter.return_value[1].typing_result = {"y": 2}
    preflight = client.post("/cluster/validate", json={"sampleIds": ["a", "b"]})
    assert preflight.status_code == 200
    assert preflight.json()["mlst"]["can_cluster"] is False
    assert preflight.json()["cgmlst"]["can_cluster"] is True

    submission = client.post(
        f"/cluster/{method}", json={"sampleIds": ["a", "b"], "method": "MSTreeV2"}
    )
    if method == "cgmlst":
        assert submission.status_code == 201
        assert schedule.call_args.args[0] is getter.return_value
    else:
        assert submission.status_code == 422
        assert submission.json()["detail"] == preflight.json()["mlst"]["notice"]
        schedule.assert_not_called()


@pytest.mark.parametrize("method", ["mlst", "cgmlst"])
def test_unknown_identity_blocks_submission_with_method_specific_notice(endpoint, method):
    client, getter, schedule = endpoint
    getter.return_value[1].scheme = None
    response = client.post(
        f"/cluster/{method}", json={"sampleIds": ["a", "b"], "method": "MSTreeV2"}
    )
    assert response.status_code == 422
    identity = "analysis profile" if method == "cgmlst" else "typing scheme"
    assert f"{identity} could not be verified" in response.json()["detail"]
    schedule.assert_not_called()


def test_unavailable_method_does_not_hide_other_preflight_results(endpoint):
    from bonsai_api.exceptions import EntryNotFound

    client, getter, _ = endpoint
    getter.side_effect = [EntryNotFound("No MLST profiles"), getter.return_value]
    response = client.post("/cluster/validate", json={"sampleIds": ["a", "b"]})
    assert response.status_code == 200
    assert response.json()["mlst"]["can_cluster"] is False
    assert response.json()["cgmlst"]["can_cluster"] is True


def test_missing_cgmlst_result_reports_profile_notice_without_blocking_mlst(endpoint):
    from bonsai_api.exceptions import EntryNotFound

    client, getter, schedule = endpoint
    message = "No cgMLST typing profile is available for the following samples: LAB-123"
    getter.side_effect = [getter.return_value, EntryNotFound(message)]
    response = client.post("/cluster/validate", json={"sampleIds": ["a", "b"]})
    assert response.status_code == 200
    assert response.json()["mlst"]["can_cluster"] is True
    assert response.json()["cgmlst"]["can_cluster"] is False
    assert "typing data is unavailable" in response.json()["cgmlst"]["notice"]
    assert response.json()["cgmlst"]["details"] == [message]
    schedule.assert_not_called()


@pytest.mark.parametrize("method", ["mlst", "cgmlst"])
def test_missing_scheme_reports_only_affected_card_names(endpoint, method):
    client, getter, schedule = endpoint
    getter.return_value[1].scheme = None
    getter.return_value[1].external_sample_id = "LAB-123"
    getter.return_value[1].sample_name = "CARD-123"
    response = client.post("/cluster/validate", json={"sampleIds": ["a", "b"]})
    assert response.status_code == 200
    validation = response.json()[method]
    assert "could not be verified" in validation["notice"]
    assert len(validation["details"]) == 1
    assert validation["details"][0].endswith(":\nCARD-123")
    assert "LAB-123" not in validation["details"][0]
    schedule.assert_not_called()


@pytest.mark.parametrize("error_type", [routes.InvalidDataFormat, ValueError])
def test_unreadable_typing_result_is_distinct_from_missing_scheme(endpoint, error_type):
    client, getter, schedule = endpoint
    message = "Invalid MLST allele profile for LAB-123: the stored allele calls could not be read."
    getter.side_effect = [error_type(message), getter.return_value]
    response = client.post("/cluster/validate", json={"sampleIds": ["a", "b"]})
    assert response.status_code == 200
    assert "stored typing results could not be read" in response.json()["mlst"]["notice"]
    assert response.json()["mlst"]["details"] == [message]
    assert response.json()["cgmlst"]["can_cluster"] is True
    schedule.assert_not_called()
