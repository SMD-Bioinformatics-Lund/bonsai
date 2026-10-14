"""Prevent unavailable AMR analyses from being displayed as negative findings."""

import pytest
from flask import render_template
from types import SimpleNamespace

from bonsai_app.blueprints.sample import views


def render_card(app, status, result=None, reason=None):
    analysis = {
        "software": "resfinder", "software_version": "4.4.1",
        "analysis_type": "amr", "status": status,
        "result": result, "reason": reason,
    }
    with app.app_context():
        return app.jinja_env.get_template("cards.html").module.amr_prediction_card(analysis)


@pytest.mark.parametrize("status", ["error", "absent", "skipped", "parsed", "unknown"])
def test_unavailable_result_has_no_negative_finding(app, status):
    html = render_card(app, status, reason="Input unavailable <script>bad</script>")
    assert "unavailable" in html.lower()
    assert "No findings" not in html
    assert "No resistance yielding" not in html
    assert "&lt;script&gt;" in html
    assert ("Analysis failed" in html) == (status == "error")


def test_failed_result_does_not_display_stale_findings(app):
    html = render_card(app, "error", {"genes": [], "variants": []})
    assert "Analysis failed" in html
    assert "No resistance yielding" not in html


@pytest.mark.parametrize("result", [None, {"genes": [], "variants": []}])
def test_successful_empty_result_is_distinct_from_unavailable(app, result):
    html = render_card(app, "empty", result)
    assert "unavailable" not in html.lower()
    assert "No findings" in html or "No resistance yielding genes identified" in html


def test_parsed_gene_antibiotics_are_displayed(app):
    gene = {"gene_symbol": "blaZ", "accession": "AP004832", "identity": 100,
            "coverage": 100, "depth": 10,
            "phenotypes": [{"name": "penicillin"}, {"name": "ampicillin"}]}
    html = render_card(app, "parsed", {"genes": [gene], "variants": []})
    assert "blaZ" in html
    assert "Penicillin, Ampicillin" in html
    assert "unavailable" not in html.lower()


@pytest.fixture()
def sample():
    return {
        "sample_id": "sample-1", "sample_name": "Sample 1", "external_sample_id": "Lab 1",
        "element_type_result": [], "species_prediction": [], "typing_result": [],
        "qc": [], "qc_status": {"status": "unprocessed"},
        "sequencing": None, "metadata": [],
        "pipeline": {"pipeline_info": {"databases": [], "definition": {}, "artifacts": [],
                                       "run_config": {"analysis_profile": []}}},
    }


@pytest.mark.parametrize("group_id", [None, "group-1"])
def test_no_amr_analysis_is_unavailable_on_sample_page(app, sample, group_id):
    with app.test_request_context():
        html = render_template("sample.html", sample=sample, group_id=group_id,
                               is_filtered=bool(group_id), bad_qc_actions=[],
                               extended=False, kw_metadata=[], metadata_tbls=[])
    assert "AMR prediction unavailable: no AMR analysis is available." in html
    assert "No predicted resistance determinants." not in html
    assert "No predicted resistance to validated phenotypes." not in html


def test_failed_amr_analysis_is_visible_on_sample_page(app, sample):
    sample["element_type_result"] = [{
        "software": "resfinder", "software_version": "4.4.1", "analysis_type": "amr",
        "status": "error", "result": None, "reason": "Invalid ResFinder input",
    }]
    with app.test_request_context():
        html = render_template("sample.html", sample=sample, group_id=None, bad_qc_actions=[],
                               extended=False, kw_metadata=[], metadata_tbls=[])
    assert "Analysis failed. Results unavailable." in html
    assert "Invalid ResFinder input" in html
    assert "No predicted resistance determinants." not in html


@pytest.mark.parametrize("status", [None, "error"])
def test_tbprofiler_page_does_not_report_unavailable_as_negative(app, sample, status):
    analyses = [] if status is None else [{
        "software": "tbprofiler", "software_version": "6.0", "analysis_type": "amr",
        "status": status, "result": None, "reason": "Invalid TBProfiler input",
    }]
    with app.test_request_context():
        html = render_template("resistance_variants.html", sample=sample, amr_results=analyses,
                               form_data={}, form_state={"selected_genes": set(),
                               "selected_types": set(), "selected_who_classes": set()},
                               antibiotics={}, rejection_reasons=[], metadata_tbls=[])
    assert "unavailable" in html.lower()
    assert "No predicted resistance determinants." not in html
    if status == "error":
        assert "Analysis failed" in html
        assert "Invalid TBProfiler input" in html


@pytest.mark.parametrize("include_result", [False, True])
def test_failed_analysis_survives_sample_page_preparation(app, sample, monkeypatch, include_result):
    analysis = {"software": "resfinder", "software_version": "4.4.1",
                "analysis_type": "amr", "status": "error", "reason": "Input invalid"}
    if include_result:
        analysis["result"] = None
    sample["element_type_result"] = [analysis]
    monkeypatch.setattr(views, "get_api_client", lambda: SimpleNamespace(
        get_sample_by_id=lambda **kwargs: sample))
    monkeypatch.setattr(views, "current_user", SimpleNamespace(token="test"))
    with app.test_request_context("/sample/sample-1"):
        html = views.sample.__wrapped__("sample-1")
    assert "Analysis failed. Results unavailable." in html
    assert "Input invalid" in html


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_failed_tbprofiler_analysis_survives_page_preparation(app, sample, monkeypatch, method):
    sample["element_type_result"] = [{
        "software": "tbprofiler", "software_version": "6.0", "analysis_type": "amr",
        "status": "error", "result": None, "reason": "Input invalid",
    }]
    monkeypatch.setattr(views, "get_api_client", lambda: SimpleNamespace(
        get_sample_by_id=lambda **kwargs: sample,
        get_antibiotics=lambda: [], get_variant_rejection_reasons=lambda: []))
    with app.test_request_context("/sample/sample-1/resistance/variants", method=method):
        html = views.resistance_variants.__wrapped__("sample-1")
    assert "Analysis failed. Results unavailable." in html
    assert "Input invalid" in html
