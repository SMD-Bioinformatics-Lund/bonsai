#!/usr/bin/env python3
"""Activate the verified seven-line authorization fix in the pilot only."""
import json
from pathlib import Path
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from common import DATA, RUN, REPO, now, write
from prepare_bonsai import main as prepare_bonsai


def request(method,path,payload=None,token=None,form=None):
    headers={}
    if token:headers['Authorization']='Bearer '+token
    if form is not None:data=urllib.parse.urlencode(form).encode()
    elif payload is not None:headers['Content-Type']='application/json';data=json.dumps(payload).encode()
    else:data=None
    req=urllib.request.Request('http://127.0.0.1:18101'+path,data=data,headers=headers,method=method)
    try:
        with urllib.request.urlopen(req,timeout=20) as response:return response.status,json.load(response)
    except urllib.error.HTTPError as error:return error.code,error.read().decode()


def main():
    fix=json.loads((RUN/'bonsai/index-auth-fix.json').read_text())
    assert fix['validation'].startswith('8 candidate')
    old=Path.home()/'data/codex/bonsai/runs/2026-11-06-species-ui/minimal-prs/2026-11-08/integration/context.json'
    parent=json.loads(old.read_text());repo=Path('/home/jakob/src/codex/bonsai')
    destination=DATA/'environments/bonsai-index-auth-pilot/source'
    if not destination.exists():
        destination.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run(['git','-C',str(repo),'worktree','add','--detach',str(destination),parent['trees']['Bonsai']['head']],check=True)
        subprocess.run(['git','-C',str(destination),'cherry-pick',fix['head']],check=True)
    head=subprocess.check_output(['git','-C',str(destination),'rev-parse','HEAD'],text=True).strip()
    # The prior completed integration tree and report evidence stay unchanged.
    context={'trees':{'Bonsai':{'path':str(destination),'head':head},'SDK':parent['trees']['SDK']},
        'candidates':{**parent['candidates'],fix['id']:fix['head']},
        'checks':[{'name':'index-write-role-boundary','status':'PASS','tests':8}],
        'parent_composition_checks':parent['checks'],'parent_app_head':parent['trees']['Bonsai']['head'],
        'change':'Existing write scope on two routes; no other production edits'}
    context_file=RUN/'bonsai/source-context.json'
    if context_file.exists():
        existing=json.loads(context_file.read_text())
        assert existing['trees']['Bonsai']['head']==head
        assert existing['candidates'][fix['id']]==fix['head']
    else:write(context_file,context)
    prepare_bonsai()
    accounts=json.loads((RUN/'bonsai/accounts.json').read_text())
    values=dict(line.split('=',1) for line in (RUN/'bonsai/compose.env').read_text().splitlines() if '=' in line)
    cases=[]
    for username,expected in [('anonymous',401),('pilot_viewer',401),('pilot_uploader',404),('pilot_admin',404)]:
        token=None
        if username!='anonymous':
            password=values['JASEN_PILOT_PASSWORD'] if username=='pilot_admin' else accounts[username]['password']
            status,body=request('POST','/token',form={'username':username,'password':password});assert status==200
            token=body['access_token']
        status,_=request('POST','/samples/pilot_deliberately_missing/ska_index',payload={'index':'/pilot/deliberately-missing.skf'},token=token)
        cases.append({'account':username,'expected_status':expected,'observed_status':status,'passed':status==expected})
    assert all(case['passed'] for case in cases),cases
    write(RUN/'bonsai/index-auth-live-retest.json',{'checked_at_utc':now(),'candidate_head':fix['head'],'pilot_app_head':head,
        'scope':'Deliberately nonexistent record; no data modified','cases':cases})
    print('Pilot authorization fix active; all four live role checks passed',flush=True)


if __name__=='__main__':main()
