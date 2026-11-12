"""Bracken species remain available in full behind a compact-table toggle."""

import pytest
from bs4 import BeautifulSoup


@pytest.mark.parametrize("count", [0, 5, 8])
@pytest.mark.parametrize("extended", [False, True])
def test_bracken_renders_all_species_and_only_long_tables_need_a_toggle(app, count, extended):
    results = [
        {"scientific_name": f"Species {index}", "fraction_total_reads": 0.9 if index == 0 else 0.00001,
         "kraken_assigned_reads": 100, "added_reads": 0}
        for index in range(count)
    ]
    template = app.jinja_env.from_string(
        '{% from "cards.html" import bracken_prediction %}'
        '{{ bracken_prediction(results, extended=extended) }}'
    )
    page = BeautifulSoup(template.render(results=results, extended=extended), "html.parser")
    container = page.select_one("[data-bracken-results]")
    rows = container.select("tbody tr")
    assert len(rows) == count
    if count:
        assert f"Species {count - 1}" in rows[-1].get_text()
    button = container.select_one("[data-bracken-toggle]")
    assert (button is not None) == (count > 5)
    # Until JavaScript initializes the toggle, every result remains accessible.
    assert not container.select("tr[hidden]")
