#!/usr/bin/env python3
"""Snapshot JASEN's public E. coli INNUENDO schema without credentialed services."""
import json
from pathlib import Path
import shutil
import subprocess
from common import DATA, RUN, ASSETS, execute, env, hashes, link, now, write


def main():
    dataset=DATA/'datasets/chewbbaca-ns/ecoli-innuendo-wgmlst/snapshot-2026-11-08'
    for directory in ['raw','derived','metadata']:(dataset/directory).mkdir(parents=True,exist_ok=True)
    receipt=dataset/'metadata/acquisition.json'
    command=execute('chewbbaca.sif','chewie','DownloadSchema','-sp','10','-sc','1','-o',dataset/'raw','--latest')
    if not receipt.exists():
        with (RUN/'schema-download.log').open('w') as output:
            subprocess.run(command,env=env(),stdout=output,stderr=subprocess.STDOUT,check=True)
        candidates=[p.parent for p in (dataset/'raw').rglob('Escherichia_coli.trn')]
        assert len(candidates)==1,candidates
        schema=candidates[0]
        inventory={str(p.relative_to(dataset/'raw')):hashes(p) for p in sorted((dataset/'raw').rglob('*')) if p.is_file()}
        write(dataset/'metadata/file-hashes.json',inventory)
        write(receipt,{'provider':'chewie-NS','endpoint':'https://chewbbaca.online/NS/api','species_id':10,'schema_id':1,
            'snapshot':'2026-11-08','acquired_at_utc':now(),'command':command,
            'raw_schema_relative_path':str(schema.relative_to(dataset/'raw')),'files':len(inventory),
            'inventory_sha256':hashes(dataset/'metadata/file-hashes.json')['sha256'],'publisher_checksum_verified':False})
    info=json.loads(receipt.read_text());schema=dataset/'raw'/info['raw_schema_relative_path']
    prepared=dataset/'derived'/schema.name
    if not prepared.exists():shutil.copytree(schema,prepared)
    link('wgmlst/escherichia_coli/alleles/ecoli_INNUENDO_wgMLST',prepared)
    write(Path(__file__).resolve().parents[2]/'datasets/jasen_pilot_schema.json',info)
    print('Public schema snapshotted and separate working copy prepared',flush=True)


if __name__=='__main__':main()
