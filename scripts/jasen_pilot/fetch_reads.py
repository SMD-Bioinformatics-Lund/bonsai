#!/usr/bin/env python3
"""Acquire the pinned benign reference-strain inputs with publisher checksums."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import md5, sha256
import json
from pathlib import Path
import subprocess

CATALOG=Path(__file__).resolve().parents[2]/'datasets/jasen_pilot_catalog.json'


def fetch(root,item):
    path=root/item['path'];part=path.with_name(path.name+'.part')
    headers=path.parent.parent/'metadata'/(path.name+'.headers.txt')
    path.parent.mkdir(parents=True,exist_ok=True)
    headers.parent.mkdir(parents=True,exist_ok=True)
    target=path if path.exists() else part
    if not path.exists():
        print('Downloading '+path.name,flush=True)
        subprocess.run(['curl','--fail','--location','--retry','5','--retry-all-errors',
            '--connect-timeout','20','--speed-time','120','--speed-limit','1024',
            '--continue-at','-','--silent','--show-error','--dump-header',str(headers),
            '--output',str(part),item['url']],check=True)
    h=md5();s=sha256();size=0
    with target.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block);s.update(block);size+=len(block)
    assert size==item['bytes'],(path.name,size,item['bytes'])
    assert h.hexdigest()==item['publisher_md5'],path.name+' checksum mismatch'
    if target==part:part.rename(path)
    print('Verified '+path.name+' ('+str(size)+' bytes)',flush=True)
    return {**item,'verified':True,'sha256':s.hexdigest(),'acquired_at_utc':item.get('acquired_at_utc',datetime.now(timezone.utc).isoformat())}


def main():
    catalog=json.loads(CATALOG.read_text());root=Path(catalog['data_root'])
    for dataset in catalog['datasets']:
        assert dataset['accession']=='ERR022075' and dataset['tax_id']==511145
        with ThreadPoolExecutor(max_workers=2) as pool:dataset['files']=list(pool.map(lambda x:fetch(root,x),dataset['files']))
    CATALOG.write_text(json.dumps(catalog,indent=2)+'\n')
    print('Both publisher MD5 checks passed; raw bytes preserved')


if __name__=='__main__':main()
