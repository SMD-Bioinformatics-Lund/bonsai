"""Render current ShigaTyper and stored legacy ShigaPass results."""

from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from bonsai_app.custom_filters import FILTERS
from bonsai_libs.parse import hydrate_result


def render_card(software, result):
    templates = Path(__file__).parents[1] / "bonsai_app/blueprints/sample/templates"
    env = Environment(
        loader=FileSystemLoader(templates),
        autoescape=True,
        undefined=StrictUndefined,
        extensions=["jinja2.ext.do"],
    )
    env.filters.update(FILTERS)
    card = env.get_template("cards.html").module.shigella_typing_card
    return BeautifulSoup(
        str(
            card(
                {
                    "analysis_type": "shigatype",
                    "software": software,
                    "software_version": "2.0.5",
                    "result": result,
                }
            )
        ),
        "html.parser",
    )


@pytest.mark.parametrize("typed", [False, True])
def test_shigatyper_card_shows_prediction_ipab_and_notes(typed):
    result = {
        "prediction": "Shigella dysenteriae serotype 3",
        "ipaB": "-",
        "notes": "<script>marker absent</script>",
    }
    if typed:
        result = hydrate_result(software="shigatyper", analysis_type="shigatype", result=result)
    card = render_card("shigatyper", result)
    assert "Shigella dysenteriae serotype 3" in card.get_text()
    assert "ipaB: -" in " ".join(card.get_text().split())
    assert "<script>marker absent</script>" in card.get_text()
    assert card.find("script") is None


def test_shigatyper_card_without_optional_values():
    card = render_card(
        "shigatyper",
        {
            "prediction": "Not Shigella or EIEC",
            "ipaB": None,
            "notes": None,
        },
    )
    assert "Not Shigella or EIEC" in card.get_text()
    assert "ipaB: –" in " ".join(card.get_text().split())
    assert card.find("table") is None
    assert "Notes" not in card.get_text()


def test_legacy_shigapass_card_keeps_serotype_and_markers():
    card = render_card(
        "shigapass",
        {
            "predicted_serotype": "Shigella sonnei",
            "predicted_flex_serotype": None,
            "rfb": "Sson",
            "mlst": None,
            "flic": None,
            "crispr": None,
            "ipah": "ipaH+",
            "comments": "legacy comment",
        },
    )
    assert "Shigella sonnei" in card.get_text()
    assert "ipaH+" in card.get_text()
    assert "legacy comment" in card.get_text()
    assert "Reads" not in card.get_text()
