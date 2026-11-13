"""Unplaced samples remain separate from the tree and safely rendered."""

import json
import pytest
from bs4 import BeautifulSoup
from bonsai_app.extensions import login_manager


def test_tree_view_lists_unplaced_samples_separately_and_escapes_labels(
    app, user_obj, monkeypatch
):
    monkeypatch.setitem(login_manager.__dict__, "_user_callback", lambda _: user_obj)
    unplaced = [
        {
            "sample_id": "empty",
            "label": "LAB <script>unsafe</script>",
            "reason": "No usable allele calls are available.",
        }
    ]
    with app.test_client(user=user_obj) as client:
        response = client.post(
            "/tree",
            data={
                "newick": "(a:1,b:0);",
                "typing_data": "mlst",
                "unplaced-samples": json.dumps(unplaced),
            },
        )
    assert response.status_code == 200
    dom = BeautifulSoup(response.data, "html.parser")
    notice = dom.select_one("#unplaced-samples")
    assert "LAB <script>unsafe</script>" in notice.get_text()
    assert notice.find("script") is None
    assert notice.find("a")["href"] == "/sample/empty"
    assert "No position or genetic distance" in notice.get_text()


@pytest.mark.parametrize(
    "bad", ["null", "{}", "[1]", '[{"sample_id":"x"}]', "not json"]
)
def test_tree_view_rejects_invalid_unplaced_sample_data(
    app, user_obj, monkeypatch, bad
):
    monkeypatch.setitem(login_manager.__dict__, "_user_callback", lambda _: user_obj)
    with app.test_client(user=user_obj) as client:
        response = client.post(
            "/tree", data={"newick": "(a:0);", "unplaced-samples": bad}
        )
    assert response.status_code == 400
