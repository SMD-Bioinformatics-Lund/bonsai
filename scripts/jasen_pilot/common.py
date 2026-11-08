"""Pinned locations and receipts for the isolated reference-strain pilot."""
from datetime import datetime, timezone
from hashlib import md5, sha256
import json
import os
from pathlib import Path
import subprocess

REPO=Path(__file__).resolve().parents[2]
DATA=Path(os.environ.get('JASEN_PILOT_DATA',Path.home()/'data/codex/jasen'))
RUN=DATA/'runs/2026-11-08-bonsai-reference-pilot'
SOURCE=DATA/'environments/upstream-v1.4.1/source'
CONTAINERS=DATA/'containers/jasen-1.4.1'
ASSETS=DATA/'analyses/bonsai-integration/2026-11-08-k12-pilot/assets'
PIN='e5e86ca8d87ec8173b6a245135b5a1858c771a5d'


def now():return datetime.now(timezone.utc).isoformat()


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+'\n')


def hashes(path):
    a=md5();b=sha256();size=0
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):a.update(block);b.update(block);size+=len(block)
    return {'bytes':size,'md5':a.hexdigest(),'sha256':b.hexdigest()}


def env():
    return dict(os.environ,SINGULARITY_CACHEDIR=str(DATA/'caches/singularity'),
        SINGULARITY_TMPDIR=str(DATA/'tmp/reference-pilot'),TMPDIR=str(DATA/'tmp/reference-pilot'),
        SINGULARITY_BINDPATH=str(DATA.resolve())+':'+str(DATA.resolve())+','+str(DATA)+':'+str(DATA),
        NXF_HOME=str(DATA/'caches/nextflow'),NXF_TEMP=str(DATA/'tmp/reference-pilot'),
        NXF_JVM_ARGS='-Xms128m -Xmx2g -XX:ActiveProcessorCount=4',NXF_ANSI_LOG='false')


def download(url,path,*,expected_md5=None,expected_sha256=None,expected_bytes=None):
    path.parent.mkdir(parents=True,exist_ok=True)
    receipt=(path.parent.parent if path.parent.name in {'raw','metadata'} else path.parent)/'metadata'/(path.name+'.receipt.json')
    part=path.with_name(path.name+'.part')
    if not path.exists():
        print('Downloading '+path.name,flush=True)
        subprocess.run(['curl','--ipv4','--fail','--location','--retry','5','--retry-all-errors','--connect-timeout','20',
            '--speed-time','120','--speed-limit','1024','--continue-at','-','--silent','--show-error',
            '--output',str(part),url],check=True,env=env())
    actual=hashes(path if path.exists() else part)
    for key,value in [('md5',expected_md5),('sha256',expected_sha256),('bytes',expected_bytes)]:
        if value is not None and actual[key]!=value:raise ValueError(path.name+' '+key+' mismatch')
    previous=json.loads(receipt.read_text()) if receipt.exists() else None
    if previous:
        if previous['sha256']!=actual['sha256']:raise ValueError('Completed payload changed: '+str(path))
    if not path.exists():part.rename(path)
    record={'url':url,'path':str(path.relative_to(DATA)),**actual,'acquired_at_utc':previous['acquired_at_utc'] if previous else now(),
        'publisher_checksum_verified':bool(expected_md5 or expected_sha256),
        'publisher_md5':expected_md5,'publisher_sha256':expected_sha256}
    write(receipt,record)
    print('Verified '+path.name,flush=True)
    return record


def run(command,log):
    print('Running '+str(command[0])+' '+str(command[1]),flush=True)
    log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('w') as out:subprocess.run(command,stdout=out,stderr=subprocess.STDOUT,check=True,env=env())


def execute(image,*arguments):
    return ['singularity','exec','--cleanenv',str(CONTAINERS/image),*map(str,arguments)]


def link(name,target):
    path=ASSETS/name;path.parent.mkdir(parents=True,exist_ok=True)
    if path.is_symlink():
        if path.resolve()!=target.resolve():raise ValueError('Existing asset link points elsewhere: '+str(path))
    elif path.exists():raise ValueError('Existing asset would be replaced: '+str(path))
    else:path.symlink_to(os.path.relpath(target,path.parent),target_is_directory=target.is_dir())
