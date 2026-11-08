#!/usr/bin/env python3
"""Save small software pins and operational entry points; payloads stay external."""
import json
import subprocess
from common import DATA, RUN, REPO, SOURCE, hashes, now, write


def main():
    images=['bonsai-species-test-'+name for name in ['api','frontend','audit_log_service','notification_service','minhash_service']]
    images+=['mongo:4.4.22','redis:7.0.10','mailhog/mailhog:latest']
    inspected=json.loads(subprocess.check_output(['docker','image','inspect',*images],text=True))
    context=json.loads((RUN/'bonsai/source-context.json').read_text())
    uploader=json.loads((DATA/'environments/prp-2.0.0/source-pin.json').read_text())
    uploader.setdefault('repository','https://github.com/SMD-Bioinformatics-Lund/bonsai-prp.git')
    scripts=[['prepare_runtime.py'],['prepare_containers.py'],['fetch_reads.py'],['prepare_assets.py','download'],
        ['prepare_assets.py','index'],['prepare_schema.py'],['prepare_reads.py'],['prepare_bonsai.py'],
        ['run_import.py','--accounts-only'],['prepare_producer_fix.py'],['prepare_pair_count_fix.py'],
        ['run_pipeline.py'],['finish_pilot.py']]
    nextflow=DATA/'environments/nextflow/25.10.4/nextflow'
    value={'captured_at_utc':now(),'source_branch':'test/jasen-public-reference-pilot','external_data_root':str(DATA),
        'run_directory':str(RUN),'scope':'One public E. coli K-12 MG1655 reference-strain software integration pilot',
        'upstream':json.loads((SOURCE.parent/'source-pin.json').read_text()),
        'local_producer_patch':json.loads((RUN/'deployment/source-context.json').read_text()),
        'uploader':uploader,
        'nextflow':{'version':'25.10.4','path':str(nextflow.relative_to(DATA)),**hashes(nextflow),
            'url':'https://github.com/nextflow-io/nextflow/releases/download/v25.10.4/nextflow-25.10.4-dist',
            'publisher_sha256_verified':True},
        'singularity_version':subprocess.check_output(['singularity','--version'],text=True).strip(),
        'java_version':subprocess.run(['java','-version'],capture_output=True,text=True,check=True).stderr.splitlines()[0],
        'pipeline_containers':json.loads((RUN/'containers.json').read_text())['containers'],
        'bonsai':context,
        'docker_images':[{'tags':x['RepoTags'],'id':x['Id'],'digests':x.get('RepoDigests',[])} for x in inspected],
        'preparation_order':[['python3','scripts/jasen_pilot/'+args[0],*args[1:]] for args in scripts],
        'status_files':[str(RUN/name) for name in ['pipeline-status.json','pilot-status.json','bonsai/import-status.json','bonsai/browser-status.json',
            'bonsai/pair-count-correction-status.json','bonsai/fidelity-status.json']],
        'new_local_fixes':[{'id':x['id'],'branch':x['branch'],'head':x['head'],'apparent_priority':x['apparent_priority']}
            for x in [json.loads((RUN/name).read_text()) for name in ['bonsai/index-auth-fix.json',
                'deployment/source-context.json','bonsai/read-pair-count-fix.json']]],
        'credentials_file':str(RUN/'bonsai/accounts.json'),
        'limitations':['One reference strain; not species-wide or clinical validation',
            'Pinned MLST container bundled database; deployment snapshots may differ',
            'Pilot uses the local minimal-fix composition rather than development directly',
            'No decision submission; single-control automatic similarity widget only'],
        'local_only':True}
    write(REPO/'datasets/jasen_pilot_software.json',value)
    print('Software pins and operational entry points captured without credentials or payloads')


if __name__=='__main__':main()
