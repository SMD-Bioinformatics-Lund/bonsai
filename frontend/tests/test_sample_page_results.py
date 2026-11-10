"""Render actual sample pages for incomplete results and optional curation data."""

import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
from bs4 import BeautifulSoup

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
