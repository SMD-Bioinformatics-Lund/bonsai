"""Bracken summary filtering preserves the compact-table toggle and full report."""

import pytest
from bs4 import BeautifulSoup


@pytest.mark.parametrize("count", [0, 4, 5, 6, 23])
@pytest.mark.parametrize("extended", [False, True])
def test_bracken_filters_summary_and_counts_only_rendered_rows_for_toggle(app, count, extended):
    results = [
        {"scientific_name": f"Species {index}", "fraction_total_reads": fraction,
         "kraken_assigned_reads": 100, "added_reads": 0}
        for index, fraction in enumerate(
            [0.001] + [0.002 + index * 0.001 for index in range(count)] + [0.00099, 0.0]
        )
    ]
    template = app.jinja_env.from_string(
        '{% from "cards.html" import bracken_prediction %}'
        '{{ bracken_prediction(results, extended=extended) }}'
    )
    page = BeautifulSoup(template.render(results=results, extended=extended), "html.parser")
    container = page.select_one("[data-bracken-results]")
    rows = container.select("tbody tr")
    visible_results = results if extended else results[1 : count + 1]
    expected = sorted(visible_results, key=lambda result: result["fraction_total_reads"], reverse=True)
    assert [row.select_one("a").get_text() for row in rows] == [
        result["scientific_name"] for result in expected
    ]
    button = container.select_one("[data-bracken-toggle]")
    assert (button is not None) == (len(expected) > 5)
    if button:
        assert button["data-bracken-toggle"] == "5"
    # Until JavaScript initializes the toggle, every result remains accessible.
    assert not container.select("tr[hidden]")
