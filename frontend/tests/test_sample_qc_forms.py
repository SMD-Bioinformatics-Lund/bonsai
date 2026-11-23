"""QC form availability and reset behavior."""

import json
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest
from bs4 import BeautifulSoup
from bonsai_app.blueprints.groups import views as group_views
from bonsai_app.blueprints.sample import views as sample_views
from bonsai_app.extensions import login_manager


@pytest.mark.parametrize("page", ["", "/metadata", "/resistance/variants"])
def test_sample_sidebar_enables_qc_on_each_tab(app, user_obj, monkeypatch, page):
    fixture = Path(__file__).parents[2] / "api/tests/data/test_ecoli_1.json"
    sample = json.loads(fixture.read_text())
    sample.update(
        sample_id="sample-a", groups=[], metadata=[], species_prediction=[],
        typing_result=[], element_type_result=[], qc_result=[],
        qc_status={"status": "failed", "action": "resequence", "comment": "Check reads"},
    )
    api = SimpleNamespace(
        get_sample_by_id=lambda **_: sample,
        get_antibiotics=lambda: [],
        get_variant_rejection_reasons=lambda: [],
    )
    monkeypatch.setattr(sample_views, "get_api_client", lambda: api)
    monkeypatch.setitem(login_manager.__dict__, "_user_callback", lambda _: user_obj)

    with app.test_client(user=user_obj) as client:
        response = client.get(f"/sample/sample-a{page}?group_id=group-a")

    assert response.status_code == 200
    dom = BeautifulSoup(response.data, "html.parser")
    form = dom.select_one("#qc-classification-form")
    assert form.select_one('option[value="resequence"]').has_attr("selected")
    assert form.select_one('label[for="unprocessed-qc-btn"]')["title"] == "Unprocessed"
    assert len(dom.find_all("script", src=re.compile(r"/sample-view(?:\.[^/]+)?\.js$"))) == 1
    init_script = next(
        script.get_text()
        for script in dom.find_all("script", src=False)
        if "initSampleSidebar(" in script.get_text()
    )
    assert 'const sampleId = "sample-a"' in init_script
    assert ("initSampleSummary(" in init_script) == (page == "")
    if page == "":
        assert 'initSampleSummary(sampleId, "group-a", api)' in init_script


@pytest.mark.parametrize(
    "views,url,sample_ids",
    [
        (sample_views, "/sample/sample-a/qc_status", ["sample-a"]),
        (group_views, "/groups/qc_status", ["sample-a", "sample-b"]),
    ],
)
def test_unprocessed_form_clears_failure_details(
    app, user_obj, monkeypatch, views, url, sample_ids
):
    update = Mock()
    api = SimpleNamespace(update_sample_qc_classification=update)
    monkeypatch.setattr(views, "get_api_client", lambda: api)
    monkeypatch.setitem(login_manager.__dict__, "_user_callback", lambda _: user_obj)

    with app.test_client(user=user_obj) as client:
        response = client.post(
            url,
            data={
                "qc-validation": "unprocessed",
                "qc-action": "resequence",
                "qc-comment": "Previous failed QC",
                "qc-selected-samples": sample_ids,
            },
            headers={"Referer": "http://localhost/groups/test-group?qc=true"},
        )

    assert response.status_code == 302
    assert update.call_args_list == [
        call(sample_id=sample_id, status="unprocessed", action=None, comment="")
        for sample_id in sample_ids
    ]
