"""The EMM card accepts the stored analysis type and reports missing results."""

import json
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from flask import render_template


@pytest.mark.parametrize("status,result,reason,expected", [
    ("parsed", {"emmtype": "emm1.0", "emm_cluster": "A-C3", "cluster_count": 0,
                "emm_like_alleles": []}, None, "emm1.0"),
    ("empty", None, "No EMM matches", "Empty EMM typing report."),
    ("absent", None, "Report unavailable", "EMM typing result is unavailable."),
])
def test_sample_summary_displays_emm_entry(app, status, result, reason, expected):
    fixture = Path(__file__).parents[2] / "api/tests/data/test_ecoli_1.json"
    sample = json.loads(fixture.read_text())
    sample.update(
        element_type_result=[], species_prediction=[], qc_result=[],
        metadata=[], qc_status={"status": "unprocessed", "action": None, "comment": ""},
        typing_result=[{"analysis_type": "emm", "software": "emmtyper",
                        "status": status, "reason": reason, "result": result}],
    )

    with app.test_request_context():
        html = render_template("sample.html", sample=sample, metadata_tbls=[],
                               bad_qc_actions=[], extended=False, group_id=None)

    assert "EMMtyper" in html
    assert expected in html
    if reason:
        assert reason in html
    if result:
        dom = BeautifulSoup(html, "html.parser")
        cluster_label = next(th for th in dom.find_all("th") if "#Clusters" in th.get_text())
        assert cluster_label.find_next_sibling("td").get_text(strip=True) == "0"
