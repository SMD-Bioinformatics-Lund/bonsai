#!/usr/bin/env python3
"""Reimport only the existing control's samtools reports through native PRP."""
import json
from prp.bonsai import BonsaiUploadService
from prp.bonsai.service import UploadStateStore
from prp.io.manifest import read_manifest
from prp.pipeline.loader import parse_manifest_for_upload
from common import RUN, REPO, now, write
from import_results import login


def main():
    file=RUN/'bonsai/pair-count-correction-status.json'
    if file.exists() and json.loads(file.read_text())['status']=='COMPLETE':
        print('Completed pair-count correction preserved');return
    original=json.loads((RUN/'bonsai/import-status.json').read_text());assert original['status']=='COMPLETE'
    sid=original['sample_id'];credentials=json.loads((RUN/'bonsai/accounts.json').read_text())['pilot_uploader']
    client=login(credentials['username'],credentials['password'])
    before=client.get_sample_by_id(sid);write(RUN/'bonsai/sample-before-pair-count.json',before)
    parsed=parse_manifest_for_upload(read_manifest(original['manifest'])).model_copy(update={'sample_id':sid})
    service=BonsaiUploadService(client=client,state_store=UploadStateStore(root=RUN/'bonsai/pair-count-upload-state'),
        workflow_id='pair-count-correction-'+sid,ignore_errors=False)
    result=service.upload_sample(parsed,force=True,only={'samtools'})
    after=client.get_sample_by_id(sid)
    old=next(x['result'] for x in before['qc_result'] if x['software']=='postalignqc')
    new=next(x['result'] for x in after['qc_result'] if x['software']=='postalignqc')
    catalog=json.loads((REPO/'datasets/jasen_pilot_catalog.json').read_text())
    pairs=catalog['datasets'][0]['derivations'][0]['read_pairs']
    assert new['n_read_pairs']==pairs and new['n_reads']==pairs*2
    assert {k:v for k,v in old.items() if k!='n_read_pairs'}=={k:v for k,v in new.items() if k!='n_read_pairs'}
    def ids(sample):return {x['analysis_id'] for key in ['typing_result','element_type_result','qc_result','species_prediction'] for x in sample[key]}
    assert len(ids(before))==len(ids(after))==original['analysis_records']
    assert before['sample_id']==after['sample_id']==result.sample_id
    assert before['pipeline']==after['pipeline']
    write(RUN/'bonsai/sample-after-pair-count.json',after)
    write(file,{'status':'COMPLETE','finished_at_utc':now(),'sample_id':sid,'only':['samtools'],'force':True,
        'before_pair_count':old['n_read_pairs'],'after_pair_count':new['n_read_pairs'],'validated_input_pairs':pairs,
        'other_qc_metrics_unchanged':True,'analysis_count_unchanged':True,'pipeline_unchanged':True,
        'scope':'Native PRP result-only reimport of the same public control; no new sample or pipeline run'})
    print('Native result-only reimport corrected count units; all other QC values and analysis count retained')


if __name__=='__main__':main()
