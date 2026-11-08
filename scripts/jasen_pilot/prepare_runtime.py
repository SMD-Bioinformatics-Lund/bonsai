#!/usr/bin/env python3
"""Recreate the exact upstream source snapshots and Nextflow used by this pilot."""
import io
import json
from pathlib import Path
import subprocess
import tarfile
from common import DATA, RUN, SOURCE, PIN, download, now, write


def snapshot(repository, upstream, commit, version, destination):
    pin=destination.parent/'source-pin.json'
    if destination.exists():
        assert json.loads(pin.read_text())['commit']==commit
        return
    subprocess.run(['git','-C',str(repository),'fetch','--no-tags',upstream,commit],check=True)
    archive=subprocess.check_output(['git','-C',str(repository),'archive',commit])
    destination.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        source.extractall(destination,filter='data')
    write(pin,{'repository':upstream,'commit':commit,'version':version,'extracted_at':now()})


def main():
    RUN.mkdir(parents=True,exist_ok=True)
    (DATA/'tmp/reference-pilot').mkdir(parents=True,exist_ok=True)
    root=Path('/home/jakob/src/codex')
    snapshot(root/'jasen','https://github.com/genomic-medicine-sweden/jasen.git',PIN,'1.4.1',SOURCE)
    snapshot(root/'bonsai-prp','https://github.com/SMD-Bioinformatics-Lund/bonsai-prp.git',
        '085ce7d3f2e475860cbe1529698e87fc17e6f801','2.0.0',DATA/'environments/prp-2.0.0/source')
    binary=DATA/'environments/nextflow/25.10.4/nextflow'
    download('https://github.com/nextflow-io/nextflow/releases/download/v25.10.4/nextflow-25.10.4-dist',binary,
        expected_sha256='60db869a7618783e3ee60183a2b0c6c50ffc67221eabec60800b904991786aaa')
    binary.chmod(0o755)
    print('Pinned source snapshots and publisher-verified Nextflow ready')


if __name__=='__main__':main()
