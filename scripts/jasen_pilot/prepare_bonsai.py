#!/usr/bin/env python3
"""Start a disposable Bonsai stack from the verified minimal-fix composition."""
import json
from pathlib import Path
import secrets
import subprocess
import time
import urllib.request
from common import DATA, RUN, REPO, ASSETS, now, write

ENV=RUN/'bonsai/compose.env'
COMPOSE=REPO/'scripts/jasen_pilot/compose.yml'


def compose(*arguments):
    config=Path.home()/'data/codex/bonsai/tools/docker-config'
    return ['docker','--config',str(config),'compose','--env-file',str(ENV),'-f',str(COMPOSE),*arguments]


def main():
    integration=Path.home()/'data/codex/bonsai/runs/2026-11-06-species-ui/minimal-prs/2026-11-08/integration'
    own_context=RUN/'bonsai/source-context.json'
    context=json.loads((own_context if own_context.exists() else integration/'context.json').read_text())
    assert all(c['status']=='PASS' for c in context['checks'])
    app=Path(context['trees']['Bonsai']['path']);sdk=Path(context['trees']['SDK']['path'])
    (app/'frontend/bonsai_app/static/build').mkdir(parents=True,exist_ok=True)
    assert subprocess.check_output(['git','-C',str(app),'rev-parse','HEAD'],text=True).strip()==context['trees']['Bonsai']['head']
    assert subprocess.check_output(['git','-C',str(sdk),'rev-parse','HEAD'],text=True).strip()==context['trees']['SDK']['head']
    (RUN/'output').mkdir(exist_ok=True);(RUN/'bonsai/mongodb').mkdir(parents=True,exist_ok=True)
    reference=DATA/'datasets/ncbi/k12-mg1655-reference/GCF_000005845.2/derived';reference.mkdir(parents=True,exist_ok=True)
    if not ENV.exists():
        values={'JASEN_PILOT_RUN':str(RUN),'JASEN_PILOT_REFERENCE':str(reference),'JASEN_PILOT_PASSWORD':secrets.token_urlsafe(18),
            'JASEN_PILOT_SECRET':secrets.token_hex(32),'BONSAI_PILOT_APP':str(app),'BONSAI_PILOT_SDK':str(sdk),
            'BONSAI_PILOT_BUILD':str(integration/'frontend-build')}
        ENV.write_text(''.join(k+'='+v+'\n' for k,v in values.items()));ENV.chmod(0o600)
    values=dict(line.split('=',1) for line in ENV.read_text().splitlines() if '=' in line)
    values['JASEN_PILOT_ASSET_GENOMES']=str(ASSETS/'genomes')
    values['BONSAI_PILOT_APP']=str(app)
    values['BONSAI_PILOT_SDK']=str(sdk)
    ENV.write_text(''.join(k+'='+v+'\n' for k,v in values.items()));ENV.chmod(0o600)
    (RUN/'bonsai/minhash').mkdir(parents=True,exist_ok=True)
    subprocess.run(compose('config','--quiet'),check=True)
    subprocess.run(compose('up','-d','mongodb','redis','mailhog','notification_service'),check=True)
    # The replica set is scoped to this compose network and fresh data directory.
    script='if (rs.status().ok !== 1) { rs.initiate({_id:"rs0",members:[{_id:0,host:"mongodb:27017"}]}); }'
    subprocess.run(compose('exec','-T','mongodb','mongo','--quiet','--eval',script),check=True)
    for _ in range(60):
        result=subprocess.run(compose('exec','-T','mongodb','mongo','--quiet','--eval','db.isMaster().ismaster'),capture_output=True,text=True)
        if 'true' in result.stdout:break
        time.sleep(1)
    else:raise RuntimeError('Isolated MongoDB did not become primary')
    subprocess.run(compose('up','-d','audit_log_service','minhash_service','api','frontend'),check=True)
    for _ in range(60):
        try:
            with urllib.request.urlopen('http://127.0.0.1:18101/',timeout=3) as response:
                if response.status==200:break
        except Exception:time.sleep(1)
    else:raise RuntimeError('Pilot API did not start')
    write(RUN/'bonsai/instance.json',{'created_at_utc':now(),'compose_project':'bonsai-jasen-pilot',
        'app_head':context['trees']['Bonsai']['head'],'sdk_head':context['trees']['SDK']['head'],
        'candidate_heads':context['candidates'],'frontend':'http://100.90.51.21:18100',
        'api':'http://127.0.0.1:18101','database_scope':'fresh isolated MongoDB replica set',
        'credentials_file':str(ENV),'compute_workers_started':['minhash_service for the pilot signature import'],
        'cross_sample_clustering_requested':False})
    print('Isolated pilot Bonsai is ready; existing test instance unchanged')


if __name__=='__main__':main()
