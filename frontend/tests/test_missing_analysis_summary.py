"""Missing AMR analyses must not be presented as negative findings."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from bonsai_app.blueprints.sample import views
from bonsai_app.extensions import login_manager


@pytest.fixture
def summary_client(app, user_obj, monkeypatch):
    fixture = Path(__file__).parents[2] / "api/tests/data/test_mtuberculosis_1.json"
    sample = json.loads(fixture.read_text())
    sample.update(
        element_type_result=[], species_prediction=[], typing_result=[],
        qc_result=[], metadata=[], reference_genome_id=None,
        qc_status={"status": "unprocessed", "action": None, "comment": ""},
    )
    api = SimpleNamespace(get_sample_by_id=lambda **kwargs: sample)
    monkeypatch.setattr(views, "get_api_client", lambda: api)
    monkeypatch.setitem(login_manager.__dict__, "_user_callback", lambda _: user_obj)
    app.config["TESTING"] = True
    with app.test_client(user=user_obj) as client:
        yield client, sample


@pytest.mark.parametrize("query", ["", "?group_id=group-1"])
@pytest.mark.parametrize("other_analysis", [False, True])
def test_missing_amr_analysis_is_unavailable(summary_client, query, other_analysis):
    client, sample = summary_client
    if other_analysis:
        sample["element_type_result"] = [{
            "software": "amrfinder", "software_version": "test",
            "analysis_type": "virulence", "result": {"genes": []},
        }]

    response = client.get(f"/sample/{sample['sample_id']}{query}")

    assert response.status_code == 200
    assert b"No stored AMR analysis is available." in response.data
    assert b"No predicted resistance determinants." not in response.data
    assert b"No predicted resistance to validated phenotypes." not in response.data


@pytest.mark.parametrize("query", ["", "?group_id=group-1"])
def test_parsed_empty_amr_result_keeps_its_negative_finding(summary_client, query):
    client, sample = summary_client
    sample["element_type_result"] = [{
        "software": "tbprofiler", "software_version": "test",
        "analysis_type": "amr", "result": {"variants": []},
    }]

    response = client.get(f"/sample/{sample['sample_id']}{query}")

    assert response.status_code == 200
    assert b"No stored AMR analysis is available." not in response.data
    assert b"No resistance yielding mutations identified" in response.data
