"""Regression coverage for submitting curations and filtering dismissed variants."""

import json
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from requests import HTTPError, Response
from werkzeug.datastructures import MultiDict

from bonsai_app.blueprints.sample import controllers, views


def test_batch_submits_each_curation_once_and_continues_after_failure():
    response = Response()
    response.status_code = 409
    response._content = b"Already curated"
    submit = Mock(side_effect=[{"id": "curation-1"}, HTTPError(response=response), {"id": "curation-3"}])
    records = [
        {"analysis_id": "analysis-1", "analysis_type": "amr", "curation": SimpleNamespace(result_key=key)}
        for key in ("variant-1", "variant-2", "variant-3")
    ]

    results = controllers.submit_curations_batch(records, create_curation_fn=submit)

    assert submit.call_count == 3
    assert [call.kwargs["record"].result_key for call in submit.call_args_list] == [
        "variant-1", "variant-2", "variant-3"
    ]
    assert [result.success for result in results] == [True, False, True]
    assert results[1].error == "HTTP 409: Already curated"


@pytest.mark.parametrize("hide_dismissed", [False, True])
def test_hide_dismissed_uses_embedded_curations_without_legacy_verified_field(hide_dismissed):
    sample = {
        "element_type_result": [{
            "result": {"variants": [{"id": key, "phenotypes": []} for key in ("rejected", "accepted", "uncurated")]},
            "curations": [
                {"result_key": "rejected", "annotation_type": "variant", "decision": "reject"},
                {"result_key": "accepted", "annotation_type": "variant", "decision": "accept"},
            ],
        }],
    }
    form = MultiDict({"hide-dismissed": "on"} if hide_dismissed else {})

    result = controllers.filter_variants(sample, form=form)

    variants = result["element_type_result"][0]["result"]["variants"]
    expected = ["accepted", "uncurated"] if hide_dismissed else ["rejected", "accepted", "uncurated"]
    assert [variant["id"] for variant in variants] == expected


def test_curation_post_renders_fresh_sample_data(app, monkeypatch):
    original = {"external_sample_id": "LAB-1", "element_type_result": [], "metadata": []}
    refreshed = {**deepcopy(original), "sample_name": "Refreshed after curation"}
    api = SimpleNamespace(
        get_sample_by_id=Mock(side_effect=[original, refreshed]),
        create_curation=Mock(return_value={"id": "curation-1"}),
        get_antibiotics=lambda: [],
        get_variant_rejection_reasons=lambda: [],
    )
    rendered = {}

    def render(template, **context):
        rendered.update(context)
        return "rendered"

    monkeypatch.setattr(views, "get_api_client", lambda: api)
    monkeypatch.setattr(views, "render_template", render)
    with app.test_request_context(
        "/sample/sample-1/resistance/variants",
        method="POST",
        data={
            "classify-variant": "1",
            "verify-variant-btn": "accept",
            "curations": json.dumps([{
                "analysis_id": "analysis-1", "analysis_type": "amr", "variant_id": "variant-1"
            }]),
        },
    ):
        assert views.resistance_variants.__wrapped__("sample-1") == "rendered"

    api.create_curation.assert_called_once()
    assert api.get_sample_by_id.call_count == 2
    assert rendered["sample"] is refreshed
