"""Stored-result display checks using generic labels and supplied values."""

from copy import deepcopy
from types import SimpleNamespace

import pytest
from flask import render_template_string
from bonsai_app.blueprints.sample import views
from test_general_ui_regressions import logged_in,pending_sample


@pytest.mark.parametrize('payload,status,expected',[
    ({'emmtype':'Supplied type','emm_cluster':'Supplied cluster','cluster_count':0,'emm_like_alleles':[]},'parsed',b'Supplied type'),
    ({},'empty',b'Empty EMM typing report'),
    (None,'error',b'EMM typing result is unavailable'),
])
def test_current_emm_descriptor_has_a_reading_surface(app,user_obj,monkeypatch,payload,status,expected):
    sample=pending_sample();sample['typing_result']=[{'analysis_type':'emm','software':'emmtyper','software_version':'0.2.0','status':status,'reason':None,'result':payload}]
    monkeypatch.setattr(views,'get_api_client',lambda:SimpleNamespace(get_sample_by_id=lambda **kwargs:deepcopy(sample)))
    with logged_in(app,monkeypatch,user_obj) as client:response=client.get('/sample/record-1')
    assert response.status_code==200
    assert expected in response.data
    if payload:assert b'<td>0</td>' in response.data


def test_short_database_link_exposes_full_version(app):
    with app.test_request_context():
        html=render_template_string("{% from 'cards.html' import make_db_link %}{{ make_db_link(db) }}",db={'name':'tbdb','version':'example-release-123456'})
    assert 'title="example-release-123456"' in html
    assert 'aria-label="Database version example-release-123456"' in html


def test_extended_summary_imports_its_record_context(app,user_obj,monkeypatch):
    # A display-only link needs the enclosing record, even inside an imported macro.
    sample=pending_sample();sample['element_type_result']=[{'analysis_type':'amr','software':'tbprofiler','software_version':'6.3.0','analysis_id':'stored',
        'curations':[],'result':{'genes':[],'phenotypes':[],'variants':[{'id':1,'reference_sequence':'supplied','start':1,'depth':10,'frequency':0.5,'phenotypes':[],'curation':None}]}}]
    sample['reference_genome_id']='stored-reference';sample['genomic_resources']={'bam':'stored.bam'}
    monkeypatch.setattr(views,'get_api_client',lambda:SimpleNamespace(get_sample_by_id=lambda **kwargs:deepcopy(sample)))
    with logged_in(app,monkeypatch,user_obj) as client:response=client.get('/sample/record-1?extended=1')
    assert response.status_code==200
    assert b'sample/record-1' in response.data
