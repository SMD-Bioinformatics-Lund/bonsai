"""Removing samples reports what the API returned."""

import json
from types import SimpleNamespace

from bonsai_app.blueprints.sample import views
from bonsai_app.extensions import login_manager


def test_remove_samples_logs_the_api_response(app, user_obj, monkeypatch):
    """The API reports n_deleted; reading any other key would break deletion."""
    calls = {}

    def fake_client():
        def delete_samples(sample_ids):
            calls["sample_ids"] = sample_ids
            # The API returns exactly these keys, see delete_many_samples.
            return {
                "sample_ids": sample_ids,
                "n_deleted": len(sample_ids),
                "remove_signature_jobs": ["job-1"],
            }

        return SimpleNamespace(delete_samples=delete_samples)

    monkeypatch.setattr(views, "get_api_client", fake_client)
    # Flask-Login otherwise reloads the user through the real API.
    monkeypatch.setitem(login_manager.__dict__, "_user_callback", lambda user_id: user_obj)

    with app.test_client(user=user_obj) as client:
        response = client.post(
            "/samples/remove",
            data={"sample-ids": json.dumps(["sample-1", "sample-2"])},
            headers={"Referer": "/samples"},
        )

    assert response.status_code == 302
    assert calls["sample_ids"] == ["sample-1", "sample-2"]
