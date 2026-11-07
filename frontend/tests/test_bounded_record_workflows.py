"""Missing-record response checks for ordinary diagnostic-software navigation."""

from types import SimpleNamespace

import pytest
from flask import render_template_string
from bonsai_libs.api_client.core.exceptions import NotFoundError
from bonsai_app.blueprints.admin import views as admin
from bonsai_app.blueprints.sample import views as samples
from bonsai_app.extensions import login_manager


@pytest.mark.parametrize("path", ["/sample/bounded-missing", "/sample/bounded-missing/metadata", "/admin/users/bounded-missing"])
def test_missing_records_return_404(app, user_obj, monkeypatch, path):
    def missing(*args, **kwargs):
        raise NotFoundError("Record not found", status=404)

    fake = SimpleNamespace(get_sample_by_id=missing, get_user=missing)
    monkeypatch.setattr(samples, "get_api_client", lambda: fake)
    monkeypatch.setattr(admin, "get_api_client", lambda: fake)
    monkeypatch.setitem(login_manager.__dict__, "_user_callback", lambda user_id: user_obj)
    with app.test_client(user=user_obj) as client:
        response = client.get(path)
    assert response.status_code == 404


def test_missing_metadata_table_returns_404(app, user_obj, monkeypatch):
    fake = SimpleNamespace(get_sample_by_id=lambda **kwargs: {
        "sample_id": "bounded-record", "external_sample_id": "bounded-record", "metadata": []})
    monkeypatch.setattr(samples, "get_api_client", lambda: fake)
    monkeypatch.setitem(login_manager.__dict__, "_user_callback", lambda user_id: user_obj)
    with app.test_client(user=user_obj) as client:
        response = client.get("/sample/bounded-record/metadata/missing")
    assert response.status_code == 404


def test_stored_null_result_keeps_the_summary_available(app, user_obj, monkeypatch):
    sample = {"sample_id": "stored-record", "sample_name": "Stored record", "external_sample_id": "stored",
        "pipeline": None, "sequencing": None, "created_at": "2026-11-07T00:00:00Z", "modified_at": "2026-11-07T00:00:00Z",
        "qc_status": {"status": "unprocessed"}, "tags": [], "comments": [], "metadata": [], "species_prediction": [],
        "typing_result": [], "qc_result": [], "element_type_result": [
            {"analysis_type": "amr", "software": "tbprofiler", "result": None, "curations": []}]}
    monkeypatch.setattr(samples, "get_api_client", lambda: SimpleNamespace(get_sample_by_id=lambda **kwargs: sample))
    monkeypatch.setitem(login_manager.__dict__, "_user_callback", lambda user_id: user_obj)
    app.context_processor(lambda: {"asset_url": lambda name: "/static/test.js"})
    with app.test_client(user=user_obj) as client:
        response = client.get("/sample/stored-record")
    assert response.status_code == 200
    assert b"Stored record" in response.data
    assert b"No stored result is available" in response.data
    assert sample["element_type_result"][0]["result"] is None


@pytest.mark.parametrize("metadata", [{}, None, {"resistance_level": "high"}])
def test_optional_stored_curation_metadata_does_not_break_rendering(app, metadata):
    analysis = {"analysis_id": "stored-analysis", "analysis_type": "amr", "result": {"variants": [
        {"id": 1, "hgvs_nt_change": "stored change", "hgvs_aa_change": "stored change", "reference_sequence": "stored",
         "accession": None, "start": 1, "variant_effect": "stored", "frequency": 0.5, "depth": 10, "phenotypes": [],
         "curation": {"decision": "accept", "phenotypes": [{"name": "rifampicin", "meta": metadata}], "rejection_reason": None}}
    ]}}
    with app.test_request_context():
        html = render_template_string("{% from 'cards.html' import tbprofiler_amr_prediction with context %}{{ tbprofiler_amr_prediction(analysis, extended=True) }}",
                                      analysis=analysis, sample={"sample_id": "stored-record"})
    assert "Accepted" in html and "Rifampicin" in html
    if metadata and metadata.get("resistance_level"):
        assert "HI" in html
