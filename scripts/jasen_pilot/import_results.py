#!/usr/bin/env python3
"""Use the pinned PRP uploader and SDK against the disposable pilot instance."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import secrets
import shutil

from bonsai_libs.api_client.bonsai.models import CreateGroupInput, CreateUserInput, CreateReferenceGenomeInput
from bonsai_libs.api_client.core.exceptions import NotFoundError
from prp.bonsai import BonsaiUploadService, make_bonsai_client
from prp.bonsai.service import UploadStateStore
from prp.io.manifest import read_manifest
from prp.pipeline.loader import parse_manifest_for_upload

from common import DATA, RUN, now, write

API='http://api:8000'
EXTERNAL='pilot_k12_err022075'


def login(username,password):
    client=make_bonsai_client(base_url=API)
    client.timeout=60
    assert client.authenticate_user(username=username,password=password),'Pilot authentication failed'
    return client


def accounts():
    values=dict(line.split('=',1) for line in (RUN/'bonsai/compose.env').read_text().splitlines() if '=' in line)
    admin=login('pilot_admin',values['JASEN_PILOT_PASSWORD'])
    file=RUN/'bonsai/accounts.json'
    if file.exists():credentials=json.loads(file.read_text())
    else:
        credentials={name:{'username':name,'password':'Pilot-A1-'+secrets.token_urlsafe(18),'roles':roles}
            for name,roles in [('pilot_viewer',['user']),('pilot_uploader',['user','uploader'])]}
        write(file,credentials);file.chmod(0o600)
    for name,account in credentials.items():
        try:admin.get_user(name)
        except NotFoundError:
            admin.create_user(CreateUserInput(**account,email=name+'@example.org',first_name='Public reference pilot',last_name=name.removeprefix('pilot_')))
        assert login(name,account['password'])
    if not any(group.group_key=='ecoli' for group in admin.get_groups()):
        admin.create_group(CreateGroupInput(group_key='ecoli',display_name='Public reference pilot',description='Isolated laboratory reference-strain software integration'))
    accession='GCF_000005845.2'
    if not any(item['accession']==accession for item in admin.request_json('GET','reference-genomes').data):
        reference=DATA/'datasets/ncbi/k12-mg1655-reference'/accession/'derived'
        payload=CreateReferenceGenomeInput(name='Public K-12 MG1655 reference',accession=accession,
            organism='Escherichia coli str. K-12 substr. MG1655',
            sequence_accessions=[line.split()[0] for line in (reference/(accession+'.fasta.fai')).read_text().splitlines()],
            fasta_resource=accession+'.fasta',fasta_index_resource=accession+'.fasta.fai')
        admin.request_json('POST','reference-genomes',json=payload.model_dump(mode='json'),expected_status=(200,201))
    write(RUN/'bonsai/accounts-status.json',{'checked_at_utc':now(),'accounts':[{k:v for k,v in a.items() if k!='password'} for a in credentials.values()],
        'ingestion_role_note':'The standard uploader reads existing records; its account has both user and uploader roles.',
        'credentials_file':str(file),'outbound_notifications':'Local MailHog sink only'})
    print('Separate viewing and read/write ingestion accounts verified',flush=True)
    return credentials


def upload():
    state_file=RUN/'bonsai/import-status.json'
    if state_file.exists() and json.loads(state_file.read_text())['status']=='COMPLETE':
        print('Completed import preserved');return
    pipeline=json.loads((RUN/'pipeline-status.json').read_text())
    assert pipeline['status']=='COMPLETE' and pipeline['tax_id']==511145
    credentials=accounts();who=credentials['pilot_uploader'];client=login(who['username'],who['password'])
    manifest_path=Path(pipeline['manifest']);manifest=read_manifest(manifest_path)
    assert manifest.sample_id==EXTERNAL and manifest.sample_name=='Public reference MG1655 (ERR022075)'
    parsed=parse_manifest_for_upload(manifest)
    assert parsed.pipeline.assay=='ecoli'
    # PRP supplies bedcov to samtools stats and suppresses legacy postalignqc
    # when stats is present; these are not separate canonical analyses.
    has_stats=any((r.software,r.subcommand)==('samtools','stats') for r in parsed.analysis_results)
    standalone=[r for r in parsed.analysis_results if (r.software,r.subcommand)!=('samtools','bedcov')
        and not (has_stats and r.software=='postalignqc' and r.subcommand is None)]
    auxiliaries=[{'software':r.software,'subcommand':r.subcommand} for r in parsed.analysis_results if r not in standalone]
    workflow_id=f'bonsai-prp-upload-{EXTERNAL}-{parsed.pipeline.pipeline_run_id}'
    store=UploadStateStore(root=RUN/'bonsai/upload-state')
    state={'status':'RUNNING','started_at_utc':now(),'manifest':str(manifest_path),'workflow_id':workflow_id,
        'account':'pilot_uploader','roles':['user','uploader'],'reports_in_manifest':len(manifest.analysis_result),
        'expected_canonical_analyses':len(standalone),'auxiliary_or_superseded_reports':auxiliaries,
        'uploader_commit':'085ce7d3f2e475860cbe1529698e87fc17e6f801','api':API}
    write(state_file,state)
    try:
        service=BonsaiUploadService(client=client,state_store=store,workflow_id=workflow_id,ignore_errors=False)
        result=service.upload_sample(parsed,force=False)
        sample=client.get_sample_by_id(result.sample_id)
        assert sample['external_sample_id']==EXTERNAL
        assert sample['sample_name']==manifest.sample_name and sample['lims_id']=='K12-PILOT-001'
        descriptors=[x for key in ['typing_result','element_type_result','qc_result','species_prediction'] for x in sample.get(key,[])]
        ids={x['analysis_id'] for x in descriptors}
        assert len(ids)==len(standalone),(len(ids),len(standalone))
        assert all(x['status']!='error' for x in descriptors)
        assert sample['pipeline']['pipeline_info']['definition']['version']=='1.4.1'
        write(RUN/'bonsai/sample-after-import.json',sample)
        shutil.copy2(manifest_path,RUN/'bonsai/producer-manifest.yaml')
        state.update(status='COMPLETE',finished_at_utc=now(),sample_id=sample['sample_id'],
            analysis_records=len(ids),view_descriptors=len(descriptors),descriptor_types=sorted({x['analysis_type'] for x in descriptors}),
            normalized_tools=sorted({x['software'] for x in descriptors}),upload_result=asdict(result))
    except Exception as error:
        state.update(status='FAILED',finished_at_utc=now(),error=str(error));write(state_file,state);raise
    write(state_file,state)
    print(f'All {len(ids)} producer reports stored; {len(descriptors)} view descriptors; identity and pipeline version preserved',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--accounts-only',action='store_true');args=parser.parse_args()
    if args.accounts_only:accounts()
    else:upload()
