"""Generic authorization regressions; services are stubbed and no files parsed."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from bonsai_api.auth import create_access_token
from bonsai_api.config import settings
from bonsai_api.crud import user as users
from bonsai_api.dependencies import get_database
from bonsai_api.routers.samples import sample_analysis


@pytest.mark.parametrize('route',['ska_index','signature'])
@pytest.mark.parametrize('role,expected',[('anonymous',401),('user',401),('uploader',200),('admin',200)])
def test_index_writes_require_existing_write_permission(route,role,expected):
    settings.api_authentication=True
    app=FastAPI();app.include_router(sample_analysis.router)
    app.dependency_overrides[get_database]=lambda:SimpleNamespace()
    account=SimpleNamespace(username='generic-'+role,roles=[role],disabled=False)
    service=AsyncMock(return_value={'add_sketch_job':'generic-job','index_job':'generic-index'})
    parse=AsyncMock(return_value='generic stub; not a biological signature')
    target='add_ska_index_service' if route=='ska_index' else 'add_sourmash_index_service'
    with patch.object(users,'get_user',AsyncMock(return_value=account)),patch.object(sample_analysis,target,service),patch.object(sample_analysis,'parse_signature_json',parse):
        with TestClient(app) as client:
            headers={} if role=='anonymous' else {'Authorization':'Bearer '+create_access_token({'sub':account.username})}
            if route=='ska_index':response=client.post('/samples/generic/ska_index',json={'index':'generic-placeholder'},headers=headers)
            else:response=client.post('/samples/generic/signature',files={'signature':('generic.txt',b'generic placeholder','text/plain')},headers=headers)
    assert response.status_code==expected
    assert service.await_count==(1 if expected==200 else 0)
    if expected==401:parse.assert_not_awaited()
