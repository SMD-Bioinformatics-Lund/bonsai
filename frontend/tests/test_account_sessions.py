"""Rejected browser identities are handled without a server-error page."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from flask import session
from bonsai_libs.api_client.core.exceptions import ApiError
from bonsai_app.blueprints.login import views


def test_disabled_session_is_cleared(app,monkeypatch):
    fake=SimpleNamespace(get_current_user=Mock(side_effect=ApiError('Inactive',status=400)))
    monkeypatch.setattr(views,'BonsaiApiClient',lambda **kwargs:fake)
    with app.test_request_context():
        session['access_token']='synthetic-token';session['_user_id']='disabled-user'
        assert views.load_user('disabled-user') is None
        assert 'access_token' not in session
        assert session[views.SESSION_ENDED_KEY] is True


def test_disabled_login_has_normal_feedback(app,monkeypatch):
    fake=SimpleNamespace(auth=SimpleNamespace(token='synthetic-token'),authenticate_user=Mock(),get_current_user=Mock(side_effect=ApiError('Inactive',status=400)))
    monkeypatch.setattr(views,'BonsaiApiClient',lambda **kwargs:fake)
    app.context_processor(lambda:{'asset_url':lambda name:'/static/test.js'})
    with app.test_client() as client:
        response=client.post('/login',data={'username':'disabled-user','password':'test'},follow_redirects=True)
    assert response.status_code==200
    assert b'Invalid login credentials' in response.data
    assert b'internal error' not in response.data
