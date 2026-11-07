"""Read-only detail availability, filter intersections and saved display decisions."""

from copy import deepcopy
from types import SimpleNamespace

import pytest
from werkzeug.datastructures import MultiDict
from bonsai_libs.api_client.core.exceptions import NotFoundError

from bonsai_app.blueprints.sample import controllers, views
from test_general_ui_regressions import logged_in, pending_sample


@pytest.mark.parametrize("path", ["/sample/record-1/resistance/variants"])
def test_missing_detail_has_a_clear_404(app, user_obj, monkeypatch, path):
    def missing(**kwargs):
        raise NotFoundError("Unavailable", status=404)
    monkeypatch.setattr(views, "get_api_client", lambda: SimpleNamespace(get_sample_by_id=missing))
    with logged_in(app, monkeypatch, user_obj) as client:
        assert client.get(path).status_code == 404


@pytest.mark.parametrize("result", [None, "absent"])
@pytest.mark.parametrize("method", ["get", "post"])
def test_unavailable_stored_detail_does_not_claim_a_negative_result(app, user_obj, monkeypatch, result, method):
    sample = pending_sample()
    if result is None:
        sample["element_type_result"] = [{"analysis_type": "amr", "software": "tbprofiler", "result": None}]
    fake = SimpleNamespace(get_sample_by_id=lambda **kwargs: deepcopy(sample), get_antibiotics=lambda: [], get_variant_rejection_reasons=lambda: [])
    monkeypatch.setattr(views, "get_api_client", lambda: fake)
    with logged_in(app, monkeypatch, user_obj) as client:
        response = getattr(client, method)("/sample/record-1/resistance/variants")
    assert response.status_code == 200
    assert b"No stored detail result is available" in response.data
    assert b"No predicted resistance determinants" not in response.data


@pytest.mark.parametrize("frequency,depth,expected", [(0.5, 30, False), (1.0, 0, False), (1.0, 30, True)])
def test_numeric_filters_require_every_condition(frequency, depth, expected):
    variant = {"frequency": frequency, "depth": depth, "phenotypes": []}
    form = MultiDict({"min-frequency": "100", "min-depth": "1", "freq-operator": "gte", "depth-operator": "gte"})
    assert controllers.has_variant_passed_filters(variant, form) is expected


def test_display_filter_handles_nonvariant_and_null_results():
    sample = {"element_type_result": [{"result": None}, {"result": {"genes": []}}]}
    original = deepcopy(sample)
    assert controllers.filter_variants(sample, MultiDict()) == original


def test_hide_dismissed_uses_stored_decisions_without_writing_them():
    variant = {"id": 1, "phenotypes": []}
    sample = {"element_type_result": [{"result": {"variants": [variant]}, "curations": [
        {"annotation_type": "variant", "result_key": "1", "decision": "reject"}]}]}
    decisions = deepcopy(sample["element_type_result"][0]["curations"])
    filtered = controllers.filter_variants(sample, MultiDict({"hide-dismissed": "on"}))
    assert filtered["element_type_result"][0]["result"]["variants"] == []
    assert sample["element_type_result"][0]["curations"] == decisions
