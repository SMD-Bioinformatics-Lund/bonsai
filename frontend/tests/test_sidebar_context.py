"""Read-only pages with stored comments receive user and retry-form context."""

from copy import deepcopy
from types import SimpleNamespace
import pytest
from bonsai_app.blueprints.sample import views
from test_general_ui_regressions import logged_in,pending_sample


@pytest.mark.parametrize('path',['/sample/record-1','/sample/record-1/metadata','/sample/record-1/resistance/variants'])
@pytest.mark.parametrize('roles',[['user'],['admin']])
def test_comment_sidebar_receives_request_context(app,user_obj,monkeypatch,path,roles):
    user_obj.roles=roles
    sample=pending_sample();sample['comments']=[{'id':1,'comment':'Generic stored comment','displayed':True,'username':'test','created_at':'2026-11-07T00:00:00Z'}]
    api=SimpleNamespace(get_sample_by_id=lambda **kwargs:deepcopy(sample),get_antibiotics=lambda:[],get_variant_rejection_reasons=lambda:[])
    monkeypatch.setattr(views,'get_api_client',lambda:api)
    with logged_in(app,monkeypatch,user_obj) as client:response=client.get(path)
    assert response.status_code==200
    assert b'Generic stored comment' in response.data
    assert (b'aria-label="Remove"' in response.data)==('admin' in roles)
    assert b'name="comment-request-id" value=""' not in response.data
