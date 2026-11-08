#!/usr/bin/env python3
"""Create a bounded, paired reference-strain input while preserving publisher reads."""
import csv
import gzip
import json
from pathlib import Path
import shutil
import subprocess
from common import DATA, RUN, REPO, execute, env, hashes, now, write

PAIRS=1_250_000
SEED=42


def identity(header):return header.split()[0].removeprefix('@').removesuffix('/1').removesuffix('/2')


def main():
    path=REPO/'datasets/jasen_pilot_catalog.json';catalog=json.loads(path.read_text());dataset=catalog['datasets'][0]
    assert dataset['accession']=='ERR022075' and dataset['tax_id']==511145
    assert all(f['verified'] for f in dataset['files'])
    root=DATA/'datasets/ena/k12-mg1655/ERR022075';destination=root/'derived/paired-seed42-1250000';destination.mkdir(parents=True,exist_ok=True)
    outputs=[];commands=[]
    for n,parent in enumerate(dataset['files'],1):
        source=DATA/parent['path'];target=destination/f'ERR022075_{n}.fastq.gz'
        command=execute('seqtk.sif','seqtk','sample','-s'+str(SEED),source,str(PAIRS));commands.append(command)
        if not target.exists():
            temporary=target.with_name(target.name+'.part')
            with temporary.open('wb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=3) as compressed:
                with subprocess.Popen(command,stdout=subprocess.PIPE,env=env()) as process:
                    shutil.copyfileobj(process.stdout,compressed,8*1024*1024)
                    assert process.wait()==0
            temporary.rename(target)
        outputs.append(target)
    records=bases=0
    with gzip.open(outputs[0],'rt') as first,gzip.open(outputs[1],'rt') as second:
        while True:
            a=[first.readline() for _ in range(4)];b=[second.readline() for _ in range(4)]
            if not a[0] and not b[0]:break
            assert all(a) and all(b) and a[0].startswith('@') and b[0].startswith('@')
            assert identity(a[0])==identity(b[0]),'Pair identifiers do not match'
            assert a[2].startswith('+') and b[2].startswith('+')
            assert len(a[1].strip())==len(a[3].strip()) and len(b[1].strip())==len(b[3].strip())
            records+=1;bases+=len(a[1].strip())+len(b[1].strip())
    assert records==PAIRS,records
    result={'kind':'paired deterministic reservoir subsample','seed':SEED,'read_pairs':records,'bases':bases,
        'created_at_utc':now(),'parent_accession':dataset['accession'],'parent_sha256':[f['sha256'] for f in dataset['files']],
        'commands':commands,'files':[{'path':str(p.relative_to(DATA)),**hashes(p)} for p in outputs],
        'pair_identifiers_validated':True,'all_record_lengths_validated':True,
        'scope':'Bounded software integration input; not a clinical or species-wide benchmark'}
    write(root/'metadata/paired-subsample.json',result)
    dataset['derivations']=[result];write(path,catalog)
    with (RUN/'samples.csv').open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=['id','platform','sequencing_run','clarity_sample_id','read1','read2','sample_name'])
        writer.writeheader();writer.writerow({'id':'pilot_k12_err022075','sample_name':'Public reference MG1655 (ERR022075)',
            'read1':str(outputs[0]),'read2':str(outputs[1]),'sequencing_run':'ENA_ERR022075','platform':'illumina','clarity_sample_id':'K12-PILOT-001'})
    print(f'Paired input ready: {records} pairs; {bases} bases; pairing and gzip verified',flush=True)


if __name__=='__main__':main()
