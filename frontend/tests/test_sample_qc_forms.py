"""Submitting Unprocessed resets failure details on either QC form."""

from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest
from bonsai_app.blueprints.groups import views as group_views
from bonsai_app.blueprints.sample import views as sample_views
from bonsai_app.extensions import login_manager


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
