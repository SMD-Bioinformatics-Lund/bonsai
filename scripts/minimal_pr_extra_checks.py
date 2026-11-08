"""Focused generic regressions for newly separated release-fix candidates.

Tests run against a selected branch's extracted source, in an isolated container.
The live database, analysis parsers and curation services are never invoked.
"""

from contextlib import contextmanager
from copy import deepcopy
from io import BytesIO
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest


@pytest.fixture
def web_app():
    from bonsai_app.app import create_app
    from flask_login import FlaskLoginClient
    app = create_app()
    app.config.update(TESTING=True, SECRET_KEY='isolated-release-check', WTF_CSRF_ENABLED=False)
    app.test_client_class = FlaskLoginClient
    app.context_processor(lambda: {'asset_url': lambda name: '/static/test.js'})
    return app


@contextmanager
def login(app, monkeypatch):
    from bonsai_app.blueprints.login.views import LoginUser
    from bonsai_app.extensions import login_manager
    user = LoginUser({'username':'admin','roles':['admin'],'authentication_method':'simple'}, token='isolated-token')
    monkeypatch.setitem(login_manager.__dict__, '_user_callback', lambda _: user)
    with app.test_client(user=user) as client:
        yield client


def record(name='Generic record'):
    return {'sample_id':'record-1','external_sample_id':'external-1','sample_name':name,'lims_id':'001',
            'pipeline':{'assay':'generic','pipeline_info':{'definition':{'name':'generic','version':'1'},
                'run_config':{'analysis_profile':[],'configuration_files':[]},'databases':[]}},
            'sequencing':{'sequencing_run_id':'generic'},'created_at':'2026-11-07T00:00:00Z',
            'modified_at':'2026-11-07T00:00:00Z','qc_status':{'status':'unprocessed'},
            'tags':[],'comments':[],'metadata':[],'species_prediction':[],'typing_result':[],
            'element_type_result':[],'qc_result':[]}


def api_app(monkeypatch, router, role='admin'):
    from fastapi import FastAPI, HTTPException
    from fastapi.security import SecurityScopes
    from bonsai_api.dependencies import get_current_user, get_database, get_audit_log, get_request_context
    from bonsai_api.config import settings, USER_ROLES
    settings.api_authentication = True
    app = FastAPI(); app.include_router(router)
    async def user(security_scopes: SecurityScopes):
        if not set(security_scopes.scopes) <= set(USER_ROLES[role]):
            raise HTTPException(401)
        return SimpleNamespace(username=role,roles=[role],disabled=False)
    app.dependency_overrides[get_current_user] = user
    app.dependency_overrides[get_database] = lambda: SimpleNamespace(client=None)
    app.dependency_overrides[get_audit_log] = lambda: None
    app.dependency_overrides[get_request_context] = lambda: SimpleNamespace(actor=SimpleNamespace(id='admin'),metadata={})
    return app


def test_ordinary_legacy_list_uses_read_permission(monkeypatch):
    from fastapi.testclient import TestClient
    from bonsai_api.routers.samples import samples
    lookup=AsyncMock(return_value={'data':[],'recordsTotal':0})
    monkeypatch.setattr(samples,'get_samples_full',lookup)
    app=api_app(monkeypatch,samples.router,role='user')
    with TestClient(app) as client:
        assert client.get('/samples').status_code==200
    lookup.assert_awaited_once()


def test_emm_projection_preserves_requested_literal_values():
    from pymongo import MongoClient
    import os
    import time
    from bonsai_api.crud.builder.summary import build_summary_entry_stages, compile_summary_pipeline
    from bonsai_api.crud.builder.summary_manifest import BUILDER_REGISTRY, MANIFEST
    client=MongoClient(os.environ['MINIMAL_AUDIT_MONGO_URI'],serverSelectionTimeoutMS=500)
    for attempt in range(30):
        try:
            client.admin.command('ping')
            break
        except Exception:
            if attempt==29:raise
            time.sleep(.2)
    collection=client.minimal_pr_check.records
    collection.insert_one({'typing_result':[{'software':'emmtyper','analysis_type':'emm',
        'result':{'emmtype':'Generic type','emm_cluster':'Generic cluster'}}]})
    stages=build_summary_entry_stages(BUILDER_REGISTRY['emm'])
    project=compile_summary_pipeline(None,MANIFEST,['emm_type','emm_cluster'])[-1]
    result=list(collection.aggregate(stages+[project]))
    assert result==[{'emm_type':'Generic type','emm_cluster':'Generic cluster'}]


def test_private_creation_is_rejected_before_the_service(monkeypatch):
    from fastapi.testclient import TestClient
    from bonsai_api.routers.samples import samples
    create = AsyncMock(return_value={'internal_sample_id':'generic'})
    monkeypatch.setattr(samples,'create_sample_service',create)
    app = api_app(monkeypatch,samples.router)
    with TestClient(app) as client:
        assert client.post('/samples/',json={'sample_id':'generic','sample_name':'Generic','visibility':'public'}).status_code == 201
        create.reset_mock()
        response = client.post('/samples/',json={'sample_id':'generic-private','sample_name':'Generic','visibility':'private'})
    assert response.status_code == 422
    create.assert_not_awaited()


def test_csv_missing_numeric_cell_round_trips_as_empty_text():
    from fastapi.responses import JSONResponse
    from bonsai_api.io import parse_metadata_table
    from bonsai_api.models.metadata import InputTableMetadata, TableMetadataInDb
    parsed = parse_metadata_table(InputTableMetadata(fieldname='Inventory',value='Item,Count\nDesk,\nChair,2\n'))
    assert parsed.data == [['Desk',''],['Chair',2]]
    JSONResponse(parsed.model_dump(mode='json'))
    legacy = TableMetadataInDb(fieldname='Inventory',category='general',columns=['Item','Count'],data=[['Desk',float('nan')]])
    assert legacy.data == [['Desk','']]
    JSONResponse(legacy.model_dump(mode='json'))


def test_single_confirmation_calls_the_service_once():
    from bonsai_app.blueprints.sample.controllers import submit_curations_batch
    create = Mock(return_value={'id':'stored'})
    item = SimpleNamespace(result_key='generic-row')
    results = submit_curations_batch([{'analysis_id':'generic-analysis','analysis_type':'generic','curation':item}],create_curation_fn=create)
    create.assert_called_once()
    assert len(results) == 1 and results[0].success


def test_confirmation_renders_refreshed_state(web_app,monkeypatch):
    from bonsai_app.blueprints.sample import views
    old,new = record('Before'),record('After stored change')
    get = Mock(side_effect=[deepcopy(old),deepcopy(new)])
    fake = SimpleNamespace(get_sample_by_id=get,create_curation=Mock(),get_antibiotics=lambda:[],get_variant_rejection_reasons=lambda:[])
    monkeypatch.setattr(views,'get_api_client',lambda:fake)
    monkeypatch.setattr(views,'build_curation_records',lambda **_:['generic-placeholder'])
    monkeypatch.setattr(views,'submit_curations_batch',lambda *_,**__:[SimpleNamespace(success=True,error=None)])
    with login(web_app,monkeypatch) as client:
        response = client.post('/sample/record-1/resistance/variants',data={
            'classify-variant':'on','verify-variant-btn':'accept','curations':json.dumps([{'id':'generic-row'}])})
    assert response.status_code == 200
    assert get.call_count == 2
    assert b'After stored change' in response.data


def test_unsupported_view_does_not_claim_no_findings(web_app,monkeypatch):
    from bonsai_app.blueprints.sample import views
    sample = record()
    sample['element_type_result'] = [{'software':'generic-unsupported','analysis_type':'amr','result':{'variants':[]}}]
    fake = SimpleNamespace(get_sample_by_id=lambda **_:deepcopy(sample),get_antibiotics=lambda:[],get_variant_rejection_reasons=lambda:[])
    monkeypatch.setattr(views,'get_api_client',lambda:fake)
    with login(web_app,monkeypatch) as client:
        for method in ['get','post']:
            response = getattr(client,method)('/sample/record-1/resistance/variants')
            assert response.status_code == 200
            assert b'Other stored result types are not displayed' in response.data
            assert b'No predicted resistance determinants' not in response.data


@pytest.mark.parametrize('method',['get','post'])
def test_null_detail_is_available_without_mutating_data(web_app,monkeypatch,method):
    from bonsai_app.blueprints.sample import views
    sample = record()
    sample['element_type_result'] = [{'software':'tbprofiler','analysis_type':'amr','result':None}]
    frozen = deepcopy(sample)
    fake = SimpleNamespace(get_sample_by_id=lambda **_:deepcopy(sample),get_antibiotics=lambda:[],get_variant_rejection_reasons=lambda:[])
    monkeypatch.setattr(views,'get_api_client',lambda:fake)
    with login(web_app,monkeypatch) as client:
        response = getattr(client,method)('/sample/record-1/resistance/variants')
    assert response.status_code == 200
    assert b'Stored variant detail results are unavailable' in response.data
    assert sample == frozen


def test_comment_header_reaches_the_idempotent_append(monkeypatch):
    from fastapi.testclient import TestClient
    from bonsai_api.routers.samples import sample_metadata
    append = AsyncMock(return_value=[])
    monkeypatch.setattr(sample_metadata,'add_comment',append)
    app = api_app(monkeypatch,sample_metadata.router)
    with TestClient(app) as client:
        response = client.post('/samples/generic/comment',headers={'Idempotency-Key':'retry-key'},json={'username':'admin','comment':'Generic note'})
    assert response.status_code == 200
    assert append.call_args.kwargs['request_key'] == 'retry-key'


def test_comment_recovery_keeps_draft_and_the_same_key(web_app,monkeypatch):
    from bonsai_app.blueprints.sample import views
    from bonsai_libs.api_client.core.exceptions import ApiError
    post = Mock(side_effect=ApiError('Response lost',status=503))
    monkeypatch.setattr(views,'get_api_client',lambda:SimpleNamespace(post_comment_to_sample=post))
    with login(web_app,monkeypatch) as client:
        response = client.post('/sample/generic/comment',data={'comment':'Draft <b> & text','comment_request_key':'retry-key'})
    assert response.status_code == 503
    assert b'Draft &lt;b&gt; &amp; text' in response.data
    assert b'value="retry-key"' in response.data
    assert post.call_args.kwargs['headers'] == {'Idempotency-Key':'retry-key'}


def test_context_free_comment_macro_gets_a_fresh_key(web_app,monkeypatch):
    from flask import render_template_string
    def view():
        return render_template_string("{% from 'sidebar.html' import comment_area %}{{ comment_area(sample) }}",sample={'sample_id':'generic','comments':[]})
    web_app.add_url_rule('/minimal-comment-form','samples.minimal_comment_form',view)
    import re
    with login(web_app,monkeypatch) as client:
        keys=[]
        for _ in range(2):
            response=client.get('/minimal-comment-form')
            assert response.status_code==200
            keys.append(re.search(rb'name="comment_request_key" value="([^"]+)"',response.data).group(1))
    assert keys[0] and keys[1] and keys[0]!=keys[1]


def test_kleborate_route_forwards_the_companion(monkeypatch):
    from fastapi.testclient import TestClient
    from bonsai_api.routers import analysis
    ingest = AsyncMock(return_value={'id':'generic'})
    monkeypatch.setattr(analysis,'ingest_analysis_service',ingest)
    app=api_app(monkeypatch,analysis.router)
    with TestClient(app) as client:
        response=client.post('/analysis/',data={'sample_id':'generic','software':'generic','software_version':'1'},
            files={'file':('generic.txt',b'generic main','text/plain'),'hamronization_file':('companion.txt',b'generic companion','text/plain')})
    assert response.status_code==201
    assert ingest.call_args.kwargs['hamronization_file'].filename=='companion.txt'


@pytest.mark.asyncio
async def test_kleborate_service_binds_the_stream_before_any_write(monkeypatch):
    from fastapi import UploadFile
    from bonsai_api.services import analysis_service
    class StopAtParser(Exception):
        pass
    observed={}
    def parser(**kwargs):
        observed.update({key:value.read() for key,value in kwargs.items() if key in ['data','hamronization_source']})
        raise StopAtParser()
    monkeypatch.setattr(analysis_service,'sample_exists',AsyncMock(return_value=True))
    monkeypatch.setattr(analysis_service,'run_parser',parser)
    with pytest.raises(StopAtParser):
        await analysis_service.ingest_analysis_service(SimpleNamespace(),sample_id='generic',software='generic',software_version='1',
            file=UploadFile(file=BytesIO(b'generic main'),filename='main.txt'),
            hamronization_file=UploadFile(file=BytesIO(b'generic companion'),filename='companion.txt'))
    assert observed=={'data':'generic main','hamronization_source':'generic companion'}


def test_sdk_companion_is_multipart_and_handles_close(tmp_path):
    from bonsai_libs.api_client.bonsai.models import UploadAnalysisResultInput
    from bonsai_libs.api_client.bonsai import samples
    owner=next(cls for cls in vars(samples).values() if isinstance(cls,type) and 'upload_analysis_result' in cls.__dict__)
    captured={}
    def send(self,path,**kwargs):
        captured.update(kwargs)
        captured['bytes']={key:value[1].read() for key,value in kwargs['files'].items()}
        return SimpleNamespace(data={'analysis_id':'generic'},headers={},status=201)
    dummy=type('GenericClient',(owner,),{'request_multipart':send})
    client=object.__new__(dummy)
    main=tmp_path/'main.txt';main.write_text('generic main')
    companion=tmp_path/'companion.txt';companion.write_text('generic companion')
    result=UploadAnalysisResultInput(sample_id='generic',software='generic',software_version='1',file=main,hamronization_file=companion)
    client.upload_analysis_result(result)
    assert captured['bytes']=={'file':b'generic main','hamronization_file':b'generic companion'}
    assert 'hamronization_file' not in captured['data']
    assert all(part[1].closed for part in captured['files'].values())
