"""QC cells expose stable search text separate from their display markup."""

import pytest
from bs4 import BeautifulSoup


@pytest.mark.parametrize("status", ["passed", "failed", "unprocessed"])
def test_qc_cell_search_value_contains_only_status(app, status):
    template = app.jinja_env.from_string(
        '{% from "cell_fmt.html" import qc_status_renderer %}{{ qc_status_renderer(qc) }}'
    )
    html = template.render(qc={"status": status, "action": "review", "comment": "QC notes"})

    cell = BeautifulSoup(html, "html.parser").find("td")
    assert cell["data-search"] == status
    assert cell.find("span").get_text(strip=True) == status
    assert "QC notes" in cell.find("i")["data-bs-title"]
