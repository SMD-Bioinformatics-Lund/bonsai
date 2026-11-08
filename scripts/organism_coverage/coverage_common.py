"""Locations for the sequential organism-coverage cases."""
import json
from pathlib import Path
import sys

REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'scripts/jasen_pilot'))
from common import DATA, CONTAINERS, PIN, SOURCE as UPSTREAM, download, hashes, env, execute, now, write

HUB=DATA/'runs/2026-11-08-organism-coverage'
ASSETS=DATA/'analyses/bonsai-integration/2026-11-08-organism-coverage/assets'
SOURCE=DATA/'environments/jasen-quoted-sample-name/source'
PILOT=DATA/'runs/2026-11-08-bonsai-reference-pilot'
CASES_FILE=REPO/'datasets/bonsai_organism_cases.json'


def cases():return json.loads(CASES_FILE.read_text())
def case_dir(key):return HUB/'cases'/key


def initialize():
    for path in [HUB/'output',HUB/'references',HUB/'bonsai',HUB/'evidence',ASSETS,DATA/'tmp/organism-coverage']:
        path.mkdir(parents=True,exist_ok=True)
    previous=DATA/'analyses/bonsai-integration/2026-11-08-k12-pilot/assets'
    for name in ['amrfinder_db','gambit_db','resfinder_db','pointfinder_db','serotypefinder_db','virulencefinder_db','plasmidfinder_db']:
        target=ASSETS/name
        if not target.exists():target.symlink_to(__import__('os').path.relpath((previous/name).resolve(),target.parent),target_is_directory=True)


def link(path,target):
    import os
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.is_symlink():assert path.resolve()==target.resolve(),path
    elif path.exists():raise RuntimeError('Existing asset would be replaced: '+str(path))
    else:path.symlink_to(os.path.relpath(target,path.parent),target_is_directory=target.is_dir())


def record_acquisition(key,kind,record):
    file=case_dir(key)/'acquisitions.json'
    current=json.loads(file.read_text()) if file.exists() else {}
    current[kind]=record;write(file,current)
    # Small source-controlled metadata catalog; no biological payloads.
    file=REPO/'datasets/bonsai_organism_acquisitions.json'
    catalog=json.loads(file.read_text()) if file.exists() else {'data_root':str(DATA),'cases':{}}
    catalog['cases'].setdefault(key,{})[kind]=record;write(file,catalog)
