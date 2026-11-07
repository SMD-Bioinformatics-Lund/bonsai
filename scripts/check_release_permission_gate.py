"""Audit real role authorization in an isolated ASGI app with a stubbed service.

No running API, database, file parser, or analysis service is contacted.
Only a generic placeholder byte string reaches the in-memory route stub.
"""

import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from bonsai_api.auth import create_access_token
from bonsai_api.config import settings,USER_ROLES
from bonsai_api.crud import user as user_crud
from bonsai_api.dependencies import get_audit_log,get_database
from bonsai_api.routers import analysis


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    settings.api_authentication=True
    rows=[]
    for role,expected in [('user',401),('uploader',201),('admin',201)]:
        app=FastAPI();app.include_router(analysis.router)
        app.dependency_overrides[get_database]=lambda:SimpleNamespace()
        app.dependency_overrides[get_audit_log]=lambda:None
        account=SimpleNamespace(username='generic-'+role,roles=[role],disabled=False)
        service=AsyncMock(return_value={'mode':'generic authorization stub'})
        with patch.object(user_crud,'get_user',AsyncMock(return_value=account)),patch.object(analysis,'ingest_analysis_service',service):
            with TestClient(app) as client:
                response=client.post('/analysis/',headers={'Authorization':'Bearer '+create_access_token({'sub':account.username})},
                    data={'sample_id':'generic-placeholder','software':'generic-contract-probe','software_version':'1.0.0'},
                    files={'file':('placeholder.txt',b'generic placeholder - not an analysis report','text/plain')})
        rows.append({'role':role,'configured_scopes':USER_ROLES[role],'expected_http_status':expected,'observed_http_status':response.status_code,
                     'stub_service_calls':service.await_count,'status':'PASS' if response.status_code==expected else 'FAIL',
                     'live_api_contacted':False,'database_contacted':False,'parser_executed':False})
    args.output.write_text(json.dumps({'method':'Real router, JWT decoding and role checks; database lookup and downstream service stubbed; container network disabled','cases':rows},indent=2)+'\n')
    for row in rows:print(row['role'],row['status'],row['observed_http_status'],'stub calls',row['stub_service_calls'])


if __name__=='__main__':main()
