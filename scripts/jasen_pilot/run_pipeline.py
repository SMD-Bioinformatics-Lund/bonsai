#!/usr/bin/env python3
"""Run the pinned upstream pipeline on the verified benign reference-strain input."""
import fcntl
import json
from pathlib import Path
import subprocess
import traceback
import re
from common import DATA, RUN, REPO, SOURCE as UPSTREAM_SOURCE, CONTAINERS, ASSETS, PIN, env, hashes, now, write
from prepare_containers import TOOLS


def main():
    context_file=RUN/'deployment/source-context.json'
    context=json.loads(context_file.read_text()) if context_file.exists() else None
    SOURCE=Path(context['path']) if context else UPSTREAM_SOURCE
    if context:
        assert context['upstream_commit']==PIN
        assert subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD'],text=True).strip()==context['head']
    with (RUN/'pipeline.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        status_file=RUN/'pipeline-status.json'
        if status_file.exists():
            previous=json.loads(status_file.read_text())
            if previous['status']=='COMPLETE':
                print('Completed pilot preserved; use a new run directory for a new experiment')
                return
            archive=RUN/'attempts';archive.mkdir(exist_ok=True)
            write(archive/('pipeline-status-'+now().replace(':','').replace('.','')+'.json'),previous)
        catalog=json.loads((REPO/'datasets/jasen_pilot_catalog.json').read_text())['datasets'][0]
        assert catalog['accession']=='ERR022075' and catalog['tax_id']==511145
        derived=catalog['derivations'][0]
        assert derived['read_pairs']==1250000 and derived['pair_identifiers_validated']
        for file in derived['files']:assert hashes(DATA/file['path'])['sha256']==file['sha256']
        assert json.loads((UPSTREAM_SOURCE.parent/'source-pin.json').read_text())['commit']==PIN
        containers=json.loads((RUN/'containers.json').read_text())
        assert {item['tool'] for item in containers['containers']}==set(TOOLS) and containers['upstream_commit']==PIN
        for tool in containers['containers']:assert (DATA/tool['path']).is_file()
        for asset in ['gambit_db','amrfinder_db/latest','resfinder_db','pointfinder_db','serotypefinder_db','virulencefinder_db','plasmidfinder_db','wgmlst/escherichia_coli/alleles/ecoli_INNUENDO_wgMLST','genomes/escherichia_coli/GCF_000005845.2.fasta.fai']:
            assert (ASSETS/asset).exists(),asset
        nxf=DATA/'environments/nextflow/25.10.4/nextflow'
        assert hashes(nxf)['sha256']=='60db869a7618783e3ee60183a2b0c6c50ffc67221eabec60800b904991786aaa'
        # Upstream deliberately ships empty installation placeholders. Nextflow
        # validates the base config before supplemental files can fill them.
        # Populate a deployment copy, preserving the original upstream bytes.
        deployment=RUN/'deployment';deployment.mkdir(exist_ok=True)
        (RUN/'completion').mkdir(exist_ok=True)
        text=(SOURCE/'nextflow.config').read_text()
        for pattern,replacement in [
            (r'^workDir\s*=\s*"".*$', 'workDir = '+json.dumps(str(RUN/'work'))),
            (r'^    outdir\s*=\s*"".*$', '    outdir = '+json.dumps(str(RUN/'output'))),
            (r'^    executor\s*=\s*"".*$', '    executor = "local"'),
            (r'^    queue\s*=\s*"".*$', '    queue = null'),
            (r'^    containers_dir\s*=.*$', '    containers_dir = '+json.dumps(str(CONTAINERS))),
            (r'^    assets_dir\s*=.*$', '    assets_dir = '+json.dumps(str(ASSETS))),
        ]:
            text,count=re.subn(pattern,replacement,text,flags=re.M);assert count==1,pattern
        text=re.sub(r"includeConfig 'conf/([^']+)'",lambda m:"includeConfig '"+str(SOURCE/'conf'/m.group(1))+"'",text)
        installed=deployment/'nextflow.config';installed.write_text(text)
        config_files=str(installed)+','+str(REPO/'scripts/jasen_pilot/pilot.config')
        with (RUN/'resolved-config.txt').open('w') as output:
            subprocess.run([str(nxf),'-C',config_files,'config',str(SOURCE),'-profile',
                'escherichia_coli,illumina,development,singularity','-flat'],cwd=RUN,env=env(),stdout=output,check=True)
        assert str(SOURCE/'containers') not in (RUN/'resolved-config.txt').read_text()
        command=[str(nxf),'-C',config_files,'-log',str(RUN/'nextflow.log'),'run',str(SOURCE/'main.nf'),
            '-profile','escherichia_coli,illumina,development,singularity',
            '-work-dir',str(RUN/'work'),'-resume']
        files=[SOURCE/'main.nf',SOURCE/'nextflow.config',*sorted((SOURCE/'conf').glob('*.config'))]
        state={'status':'RUNNING','started_at_utc':now(),'upstream_commit':PIN,'upstream_version':'1.4.1',
            'dataset':'ERR022075','tax_id':511145,'read_pairs':derived['read_pairs'],'input_files':derived['files'],
            'local_producer_patch':context,
            'command':command,'source_hashes':{str(p.relative_to(SOURCE)):hashes(p)['sha256'] for p in files},
            'overlay_sha256':hashes(REPO/'scripts/jasen_pilot/pilot.config')['sha256'],
            'deployment_config_sha256':hashes(installed)['sha256'],
            'resource_limits':{'cpus':4,'memory_gb':18,'concurrent_tasks':1},
            'database_deviation':'Pinned MLST container bundled database; live credentialed PubMLST snapshot not used',
            'scope':'One public laboratory reference-strain integration run; no clinical validation'}
        write(RUN/'pipeline-status.json',state)
        try:
            with (RUN/'pipeline.stdout.log').open('a') as output:
                subprocess.run(command,cwd=RUN,env=env(),stdout=output,stderr=subprocess.STDOUT,check=True)
            output=RUN/'output/ecoli/analysis_yaml/pilot_k12_err022075.yaml'
            assert output.is_file(),'Upstream pipeline did not publish the sample manifest'
            state.update(status='COMPLETE',finished_at_utc=now(),manifest=str(output),manifest_sha256=hashes(output)['sha256'])
        except Exception as error:
            state.update(status='FAILED',finished_at_utc=now(),error=str(error))
            write(RUN/'pipeline-status.json',state)
            raise
        write(RUN/'pipeline-status.json',state)
        print('Pinned upstream reference-strain pilot completed; manifest and resource trace saved',flush=True)


if __name__=='__main__':main()
