"""The shared TB table displays existing results in numeric genomic order."""

import pytest
from bs4 import BeautifulSoup
from flask import render_template_string


@pytest.mark.parametrize("extended", [False, True])
def test_tb_table_orders_positions_independently_of_gene_and_curation(app, extended):
    variants = [
        {
            "id": index, "start": position, "reference_sequence": gene,
            "accession": "CCP43410", "hgvs_nt_change": "c.10A>G",
            "hgvs_aa_change": None, "variant_effect": "missense_variant",
            "depth": 100, "frequency": 1,
            "phenotypes": [{"name": "rifampicin", "source": None, "note": ""}],
            "curation": {"decision": decision, "phenotypes": [], "rejection_reason": None},
        }
        for index, (position, gene, decision) in enumerate(
            [(1000, "aaa", "accept"), (9, "zzz", "reject"), (100, "mmm", None)], 1
        )
    ]
    with app.test_request_context():
        html = render_template_string(
            "{% from 'cards.html' import tbprofiler_amr_prediction with context %}"
            "{{ tbprofiler_amr_prediction(analysis, extended=extended) }}",
            analysis={"analysis_id": "analysis-1", "analysis_type": "amr", "result": {"variants": variants}},
            sample={"sample_id": "tb-1"}, extended=extended,
        )
    table = BeautifulSoup(html, "html.parser").select_one("#tb-profiler-variant-tbl")
    headings = [cell.get_text(strip=True) for cell in table.select("thead tr > td")]
    column = headings.index("Genomic position (1-based)")
    rows = table.select("tbody > tr")
    assert [row.select("td")[column].get_text(strip=True) for row in rows] == ["9", "100", "1000"]
    assert [variant["id"] for variant in variants] == [1, 2, 3]
    assert len(table.select("thead .no-sort")) == (2 if extended else 0)
    if extended:
        assert [cb["data-variant-id"] for cb in table.select("tbody input")] == ["2", "3", "1"]
