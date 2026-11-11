"""E. coli summaries show STX findings, empty analyses, and missing analyses."""

import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
from bs4 import BeautifulSoup

from bonsai_app.blueprints.sample import views
from bonsai_app.extensions import login_manager


@pytest.fixture
def stx_page(app, user_obj, monkeypatch):
    fixture = Path(__file__).parents[2] / "api/tests/data/test_ecoli_1.json"
    sample = json.loads(fixture.read_text())
    sample.update(
        element_type_result=[], species_prediction=[], typing_result=[],
        qc_result=[], metadata=[], reference_genome_id=None,
        qc_status={"status": "unprocessed", "action": None, "comment": ""},
        created_at="2026-11-11T10:00:00+00:00",
        modified_at="2026-11-11T10:00:00+00:00",
    )
    analysis = {
        "analysis_type": "stx", "software": "virulencefinder",
        "software_version": "3.0.0", "status": "empty", "result": None,
    }
    sample["typing_result"] = [analysis]
    api = SimpleNamespace(get_sample_by_id=lambda **kwargs: deepcopy(sample))
    monkeypatch.setattr(views, "get_api_client", lambda: api)
    monkeypatch.setitem(login_manager.__dict__, "_user_callback", lambda _: user_obj)
    app.config["TESTING"] = True
    with app.test_client(user=user_obj) as client:
        yield client, sample, analysis


def get_stx_card(response):
    assert response.status_code == 200
    page = BeautifulSoup(response.data, "html.parser")
    cards = [
        card for card in page.select("#epi-typing-heading .card")
        if "STX typing" in card.select_one(".card-header").get_text()
    ]
    assert len(cards) == 1
    return cards[0]


@pytest.mark.parametrize("query", ["", "?group_id=group-1", "?extended=1"])
@pytest.mark.parametrize("result", [None, {}, {"hits": []}])
def test_empty_stx_analysis_keeps_card_with_no_hits_message(stx_page, query, result):
    client, sample, analysis = stx_page
    analysis["result"] = result

    card = get_stx_card(client.get(f"/sample/{sample['sample_id']}{query}"))

    assert "No STX genes identified." in card.get_text()
    assert "unavailable" not in card.get_text()
    assert "virulencefinder v3.0.0" in card.get_text()
    assert card.select_one("tbody td")["colspan"] == "5"


@pytest.mark.parametrize("status", ["absent", "error"])
def test_unavailable_stx_analysis_is_not_reported_as_no_hits(stx_page, status):
    client, sample, analysis = stx_page
    analysis.update(status=status, reason="Report unavailable")

    card = get_stx_card(client.get(f"/sample/{sample['sample_id']}"))

    assert "STX typing result is unavailable." in card.get_text()
    assert "No STX genes identified." not in card.get_text()


def test_ecoli_without_stored_stx_analysis_still_has_card(stx_page):
    client, sample, _ = stx_page
    sample["typing_result"] = []

    card = get_stx_card(client.get(f"/sample/{sample['sample_id']}"))

    assert "STX typing result is unavailable." in card.get_text()
    assert "No STX genes identified." not in card.get_text()
    assert "virulencefinder" not in card.get_text()


@pytest.mark.parametrize("assay", [None, "saureus"])
def test_other_assays_without_stx_analysis_do_not_gain_stx_card(stx_page, assay):
    client, sample, _ = stx_page
    sample["typing_result"] = []
    sample["pipeline"]["assay"] = assay

    response = client.get(f"/sample/{sample['sample_id']}")

    assert response.status_code == 200
    page = BeautifulSoup(response.data, "html.parser")
    assert "STX typing" not in page.select_one("#epi-typing-heading").get_text()


@pytest.mark.parametrize("legacy", [False, True])
def test_stx_hits_remain_visible_without_an_extra_card(stx_page, legacy):
    client, sample, analysis = stx_page
    gene = {
        "accession": "AB015057", "gene_symbol": "stx2", "ref_database": "stx-db",
        "coverage": 100.0, "identity": 99.5, "sequence_name": "STX hit",
    }
    second_gene = {**gene, "accession": "M19473", "gene_symbol": "stx1"}
    analysis.update(
        status="parsed", result=gene if legacy else {"hits": [gene, second_gene]}
    )

    card = get_stx_card(client.get(f"/sample/{sample['sample_id']}"))

    rows = card.select("tbody tr")
    assert len(rows) == (1 if legacy else 2)
    assert "stx2" in rows[0].get_text()
    assert "stx-db" in rows[0].get_text()
    assert "100.0%" in rows[0].get_text()
    assert "99.5%" in rows[0].get_text()
    if not legacy:
        assert "stx1" in rows[1].get_text()
    assert "No STX genes identified." not in card.get_text()
    assert "unavailable" not in card.get_text()
