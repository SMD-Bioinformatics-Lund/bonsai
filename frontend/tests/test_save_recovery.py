"""Failed comment submissions retain an escaped draft and stable retry identity."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from flask import render_template_string
from bonsai_libs.api_client.core.exceptions import ApiError
from bonsai_app.blueprints.sample import views
from bonsai_app.extensions import login_manager


@pytest.mark.parametrize("status", [503, 409])
def test_failed_comment_keeps_draft_and_request_key(app, user_obj, monkeypatch, status):
    post = Mock(side_effect=ApiError("Temporary problem", status=status))
    monkeypatch.setattr(views, "get_api_client", lambda: SimpleNamespace(post_comment_to_sample=post))
    monkeypatch.setitem(login_manager.__dict__, "_user_callback", lambda user_id: user_obj)
    # Render the real comment macro without unrelated sample/result services.
    def sample(sample_id, **context):
        return render_template_string("{% from 'sidebar.html' import comment_area with context %}{{ comment_area(sample) }}",
            sample={"sample_id": sample_id, "comments": []}, comment_draft=views.request.form.get("comment", ""),
            comment_request_id=views.request.form.get("comment-request-id"))
    monkeypatch.setattr(views, "sample", sample)
    with app.test_client(user=user_obj) as client:
        response = client.post("/sample/record/comment", data={"comment": "Draft <script> & text", "comment-request-id": "retry-1"})
    assert response.status_code == status
    assert b"Draft &lt;script&gt; &amp; text" in response.data
    assert b'value="retry-1"' in response.data
    assert post.call_args.kwargs["headers"] == {"Idempotency-Key": "retry-1"}


def test_successful_comment_redirects_with_confirmation(app, user_obj, monkeypatch):
    post = Mock()
    monkeypatch.setattr(views, "get_api_client", lambda: SimpleNamespace(post_comment_to_sample=post))
    monkeypatch.setitem(login_manager.__dict__, "_user_callback", lambda user_id: user_obj)
    with app.test_client(user=user_obj) as client:
        response = client.post("/sample/record/comment", data={"comment": "Draft", "comment-request-id": "retry-1"})
        with client.session_transaction() as session:
            assert any("Comment added" in text for category, text in session["_flashes"])
    assert response.status_code == 302


def test_comment_removal_denial_has_normal_feedback(app, user_obj, monkeypatch):
    remove = Mock(side_effect=ApiError("Permission denied", status=401))
    monkeypatch.setattr(views, "get_api_client", lambda: SimpleNamespace(remove_comment_from_sample=remove))
    monkeypatch.setitem(login_manager.__dict__, "_user_callback", lambda user_id: user_obj)
    with app.test_client(user=user_obj) as client:
        response = client.post("/sample/record/comment/1")
        with client.session_transaction() as session:
            assert any("comment could not be removed" in text for category, text in session["_flashes"])
    assert response.status_code == 302


@pytest.mark.parametrize("roles,visible", [(["user"], False), (["admin"], True)])
def test_comment_removal_control_follows_role(app, user_obj, monkeypatch, roles, visible):
    user_obj.roles = roles
    monkeypatch.setitem(login_manager.__dict__, "_user_callback", lambda user_id: user_obj)
    with app.test_request_context():
        from flask_login import login_user
        login_user(user_obj)
        html = render_template_string("{% from 'sidebar.html' import comment_area with context %}{{ comment_area(sample) }}",
            sample={"sample_id": "record", "comments": [{"id": 1, "comment": "Text", "displayed": True,
                "username": "user", "created_at": "2026-11-07T00:00:00Z"}]})
    assert ('aria-label="Remove"' in html) == visible
