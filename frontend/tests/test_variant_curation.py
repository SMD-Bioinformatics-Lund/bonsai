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
    original = {
        "external_sample_id": "LAB-1", "metadata": [],
        "element_type_result": [{
            "analysis_id": "analysis-1", "analysis_type": "amr", "software": "tbprofiler",
            "result": {"variants": [{
                "id": "variant-1", "reference_sequence": "gene-1",
                "variant_type": "snp", "phenotypes": [],
            }]},
        }],
    }
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


@pytest.mark.parametrize("decision,reason", [(None, None), ("reject", None)])
def test_curation_requires_a_decision_and_rejection_reason(decision, reason):
    with pytest.raises(ValueError):
        controllers.build_curation_records(
            [{"analysis_id": "a", "analysis_type": "amr", "variant_id": "0"}],
            decision=decision, rejection_reason=reason,
        )


@pytest.mark.parametrize("depth_operator,depth", [("gte", 100), ("lte", 10)])
def test_depth_filter_does_not_override_failed_frequency_filter(depth_operator, depth):
    form = MultiDict({
        "min-frequency": "50", "freq-operator": "gte",
        "min-depth": "50", "depth-operator": depth_operator,
    })
    assert not controllers.has_variant_passed_filters(
        {"frequency": 0.1, "depth": depth, "phenotypes": []}, form
    )


@pytest.mark.parametrize("approved_by", [None, "reviewer"])
@pytest.mark.parametrize("modified_at", [None, "2026-11-10"])
def test_curation_merge_keeps_authors_separate_from_last_modification(approved_by, modified_at):
    analysis = {
        "result": {"variants": [{"id": 0}]},
        "curations": [{
            "id": "existing", "annotation_type": "variant", "result_key": "0",
            "decision": "accept", "curated_by": "second-user",
            "created_at": "2025-01-01", "modified_at": modified_at,
            "approved_by": approved_by,
        }],
    }
    controllers.merge_variants_with_curations(analysis)
    merged = analysis["result"]["variants"][0]["curation"]
    assert merged["curated_by"] == "second-user"
    assert merged["approved_by"] == approved_by
    assert merged["modified_at"] == (modified_at or "2025-01-01")
    assert "curated_at" not in merged
