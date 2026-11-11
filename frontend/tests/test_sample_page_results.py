"""Render actual sample pages for incomplete results and optional curation data."""

import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
from bs4 import BeautifulSoup
from unittest.mock import Mock
from bonsai_libs.api_client.core.exceptions import ConflictError

from bonsai_app.blueprints.sample import views
from bonsai_app.extensions import login_manager


@pytest.fixture
def sample_page(app, user_obj, monkeypatch):
    fixture = Path(__file__).parents[2] / "api/tests/data/test_mtuberculosis_1.json"
    sample = json.loads(fixture.read_text())
    prediction = next(
        entry for entry in sample["element_type_result"]
        if entry["software"] == "tbprofiler" and entry["analysis_type"] == "amr"
    )
    prediction["result"]["variants"] = prediction["result"]["variants"][:1]
    prediction["curations"] = []
    sample.update(
        element_type_result=[prediction], species_prediction=[], typing_result=[],
        qc_result=[], reference_genome_id=None,
        metadata=[], qc_status={"status": "unprocessed", "action": None, "comment": ""},
    )
    api = SimpleNamespace(
        get_sample_by_id=lambda **kwargs: deepcopy(sample),
        get_antibiotics=lambda: [],
        get_variant_rejection_reasons=lambda: [],
    )
    monkeypatch.setattr(views, "get_api_client", lambda: api)
    monkeypatch.setitem(login_manager.__dict__, "_user_callback", lambda _: user_obj)
    app.config["TESTING"] = True
    with app.test_client(user=user_obj) as client:
        yield client, sample, prediction


@pytest.mark.parametrize("page", ["", "/resistance/variants"])
@pytest.mark.parametrize("meta", [None, {}, {"resistance_level": "high"}])
def test_curated_phenotypes_render_without_optional_metadata(sample_page, page, meta):
    client, sample, prediction = sample_page
    variant = prediction["result"]["variants"][0]
    prediction["curations"] = [{
        "annotation_type": "variant", "result_key": str(variant["id"]),
        "decision": "accept", "phenotypes": [{"name": "rifampicin", "meta": meta}],
    }]

    response = client.get(f"/sample/{sample['sample_id']}{page}")

    assert response.status_code == 200
    assert b"Accepted" in response.data
    assert b"Rifampicin" in response.data
    assert (b'data-bs-title="High"' in response.data) == bool(meta)


@pytest.mark.parametrize("page", ["", "/resistance/variants"])
def test_null_amr_result_renders_an_unavailable_message(sample_page, page):
    client, sample, prediction = sample_page
    prediction["result"] = None
    prediction["status"] = "absent"

    response = client.get(f"/sample/{sample['sample_id']}{page}")

    assert response.status_code == 200
    assert b"unavailable" in response.data or b"No stored result" in response.data


def test_filters_tolerate_null_amr_results(sample_page):
    client, sample, prediction = sample_page
    prediction["result"] = None

    response = client.post(
        f"/sample/{sample['sample_id']}/resistance/variants",
        data={"hide-dismissed": "on"},
    )

    assert response.status_code == 200
    assert b"Stored variant detail results are unavailable" in response.data


def test_non_tbprofiler_result_is_not_presented_as_a_negative_finding(sample_page):
    client, sample, prediction = sample_page
    prediction["software"] = "amrfinder"

    response = client.get(f"/sample/{sample['sample_id']}/resistance/variants")

    assert response.status_code == 200
    assert b"Other stored result types are not displayed here" in response.data
    assert b"No predicted resistance determinants" not in response.data


def test_extended_summary_links_identify_the_sample_and_analysis(sample_page):
    client, sample, prediction = sample_page

    response = client.get(f"/sample/{sample['sample_id']}?extended=1")

    assert response.status_code == 200
    dom = BeautifulSoup(response.data, "html.parser")
    igv_links = [link["href"] for link in dom.find_all("a") if link.get_text(strip=True) == "IGV"]
    assert igv_links
    assert all(sample["sample_id"] in href for href in igv_links)
    assert all(prediction["analysis_id"] in href for href in igv_links)


@pytest.mark.parametrize("page", ["", "/resistance/variants"])
def test_variant_zero_and_manually_annotated_resistance_remain_visible(sample_page, page):
    client, sample, prediction = sample_page
    variant = prediction["result"]["variants"][0]
    variant.update(id=0, phenotypes=[])
    prediction["curations"] = [{
        "id": "curation-zero", "annotation_type": "variant", "result_key": "0",
        "decision": "accept", "phenotypes": [{"name": "rifampicin"}],
    }]

    response = client.get(f"/sample/{sample['sample_id']}{page}")

    assert response.status_code == 200
    assert b"Accepted" in response.data
    assert b"Rifampicin" in response.data
    assert b"No resistance yeilding mutations identified" not in response.data
    if page:
        assert b"Remove curation" in response.data
        response = client.post(
            f"/sample/{sample['sample_id']}{page}", data={"yeild-resistance": "on"}
        )
        assert b"Rifampicin" in response.data


@pytest.mark.parametrize("decision", ["accept", "reject"])
def test_existing_variant_curation_is_updated_instead_of_created(sample_page, decision):
    client, sample, prediction = sample_page
    variant = prediction["result"]["variants"][0]
    prediction["curations"] = [{
        "id": "existing", "annotation_type": "variant", "result_key": str(variant["id"]),
        "decision": "accept", "phenotypes": [],
    }]
    api = views.get_api_client()
    api.create_curation = Mock()
    api.request_json = Mock(return_value=SimpleNamespace(data={"curation_id": "existing"}))
    api.get_variant_rejection_reasons = lambda: [{"label": "test", "description": "Test reason"}]

    response = client.post(
        f"/sample/{sample['sample_id']}/resistance/variants",
        data={
            "classify-variant": "1", "verify-variant-btn": decision,
            "rejection-reason": "test", "amrs": ["rifampicin"], "resistance-lvl-btn": "low",
            "curations": json.dumps([{
                "analysis_id": prediction["analysis_id"], "analysis_type": "amr",
                "variant_id": str(variant["id"]),
            }]),
        },
    )

    assert response.status_code == 200
    api.create_curation.assert_not_called()
    api.request_json.assert_called_once()
    call = api.request_json.call_args
    assert call.args == ("PUT", "analysis/curations/existing")
    assert call.kwargs["json"] == {
        "decision": decision,
        "rejection_reason": "Test reason" if decision == "reject" else None,
        "phenotypes": [{"name": "rifampicin", "meta": {"resistance_level": "low"}}],
    }
    assert b"Successfully saved 1 curation(s)" in response.data


def test_save_rejects_variants_from_another_sample(sample_page):
    client, sample, prediction = sample_page
    api = views.get_api_client()
    api.create_curation = Mock()
    api.request_json = Mock()

    response = client.post(
        f"/sample/{sample['sample_id']}/resistance/variants",
        data={
            "classify-variant": "1", "verify-variant-btn": "accept",
            "curations": json.dumps([{
                "analysis_id": "another-sample-analysis", "analysis_type": "amr", "variant_id": "0",
            }]),
        },
    )

    assert response.status_code == 200
    assert b"Selected variants are no longer available for this sample" in response.data
    api.create_curation.assert_not_called()
    api.request_json.assert_not_called()


@pytest.mark.parametrize("belongs_to_sample", [False, True])
def test_remove_curation_checks_sample_and_returns_to_variant_view(sample_page, belongs_to_sample):
    client, sample, prediction = sample_page
    variant = prediction["result"]["variants"][0]
    if belongs_to_sample:
        prediction["curations"] = [{
            "id": "existing", "annotation_type": "variant", "result_key": str(variant["id"]),
            "decision": "accept", "phenotypes": [],
        }]
    api = views.get_api_client()
    api.delete = Mock(side_effect=lambda *args, **kwargs: prediction.update(curations=[]))

    response = client.post(f"/sample/{sample['sample_id']}/curation/existing/remove", follow_redirects=True)

    assert response.status_code == 200
    if belongs_to_sample:
        api.delete.assert_called_once_with("analysis/curations/existing", expected_status=(204,))
        assert b"Curation removed" in response.data
        assert b"Accepted" not in response.data
    else:
        api.delete.assert_not_called()
        assert b"no longer available for this sample" in response.data
    assert b"Remove curation" not in response.data


def test_update_failure_shows_readable_message_and_keeps_existing_curation(sample_page):
    client, sample, prediction = sample_page
    variant = prediction["result"]["variants"][0]
    prediction["curations"] = [{
        "id": "existing", "annotation_type": "variant", "result_key": str(variant["id"]),
        "decision": "accept", "phenotypes": [],
    }]
    api = views.get_api_client()
    api.create_curation = Mock()
    api.request_json = Mock(side_effect=ConflictError(
        "Conflict", status=409, body='{"detail":"This curation changed. Reload and try again."}'
    ))
    response = client.post(
        f"/sample/{sample['sample_id']}/resistance/variants",
        data={
            "classify-variant": "1", "verify-variant-btn": "accept",
            "curations": json.dumps([{
                "analysis_id": prediction["analysis_id"], "analysis_type": "amr",
                "variant_id": str(variant["id"]),
            }]),
        },
    )
    assert response.status_code == 200
    assert b"This curation changed. Reload and try again." in response.data
    assert b"Accepted" in response.data
    api.create_curation.assert_not_called()


@pytest.mark.parametrize("page", ["", "/resistance/variants"])
@pytest.mark.parametrize("approved_by", [None, "reviewer"])
@pytest.mark.parametrize("modified_at", [None, "2026-11-11T12:00:00"])
def test_curation_tooltip_labels_modification_time_and_authors(
    sample_page, app, page, approved_by, modified_at,
):
    client, sample, prediction = sample_page
    variant = prediction["result"]["variants"][0]
    created_at = "2025-01-01T10:00:00"
    prediction["curations"] = [{
        "id": "existing", "annotation_type": "variant", "result_key": str(variant["id"]),
        "decision": "reject", "rejection_reason": "Needs review", "phenotypes": [],
        "curated_by": "annotation-author", "approved_by": approved_by,
        "created_at": created_at, "modified_at": modified_at,
    }]

    response = client.get(f"/sample/{sample['sample_id']}{page}")

    assert response.status_code == 200
    dom = BeautifulSoup(response.data, "html.parser")
    tooltip = next(
        element["data-bs-title"] for element in dom.select("[data-bs-title]")
        if "Curated by:" in element["data-bs-title"]
    )
    text = BeautifulSoup(tooltip, "html.parser").get_text(" ", strip=True)
    expected_time = app.jinja_env.filters["strftime"](modified_at or created_at, "%c")
    assert "Curated by: annotation-author" in text
    assert f"Last modified: {expected_time}" in text
    assert "Curated at:" not in text
    if approved_by:
        assert "Approved by: reviewer" in text
    else:
        assert "Approved by:" not in text
