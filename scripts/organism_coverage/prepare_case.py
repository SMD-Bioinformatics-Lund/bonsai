#!/usr/bin/env python3
"""Prepare one selected ordinary reference/benchmark case, preserving source data."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import gzip
import json
from pathlib import Path
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
import zipfile
from coverage_common import *


def metadata(url,path):
    if not path.exists():download(url,path)
    return json.loads(path.read_text())


def reads(key,case):
    root=DATA/'datasets/ena'/case['dataset']/case['accession']
    for d in ['raw','derived','metadata']:(root/d).mkdir(parents=True,exist_ok=True)
    url='https://www.ebi.ac.uk/ena/portal/api/filereport?'+urllib.parse.urlencode({'accession':case['accession'],
        'result':'read_run','fields':'run_accession,study_accession,sample_accession,scientific_name,tax_id,sample_title,sample_alias,library_strategy,library_source,library_layout,instrument_platform,fastq_ftp,fastq_md5,fastq_bytes','format':'json'})
    rows=metadata(url,root/'metadata/read-run.json');assert len(rows)==1
    row=rows[0];assert row['library_strategy']=='WGS' and row['library_source']=='GENOMIC'
    assert row['library_layout']=='PAIRED' and row['instrument_platform']=='ILLUMINA'
    jobs=list(zip(row['fastq_ftp'].split(';'),row['fastq_md5'].split(';'),row['fastq_bytes'].split(';')));assert len(jobs)==2
    def one(job):
        location,checksum,size=job
        return download('https://'+location,root/'raw'/Path(location).name,expected_md5=checksum,expected_bytes=int(size))
    with ThreadPoolExecutor(max_workers=2) as pool:files=list(pool.map(one,jobs))
    record_acquisition(key,'reads',{'metadata_url':url,'metadata':row,'files':files})
    receipt=root/'metadata/pair-validation.json'
    if not receipt.exists():
        count=bases=0
        with gzip.open(DATA/files[0]['path'],'rt') as first,gzip.open(DATA/files[1]['path'],'rt') as second:
            while True:
                a=[first.readline() for _ in range(4)];b=[second.readline() for _ in range(4)]
                if not a[0] and not b[0]:break
                assert all(a) and all(b)
                name=lambda value:value.split()[0].removeprefix('@').removesuffix('/1').removesuffix('/2')
                assert name(a[0])==name(b[0])
                assert all(x[0].startswith('@') and x[2].startswith('+') and len(x[1].strip())==len(x[3].strip()) for x in [a,b])
                count+=1;bases+=len(a[1].strip())+len(b[1].strip())
        write(receipt,{'validated_at_utc':now(),'read_pairs':count,'bases':bases,'parent_sha256':[x['sha256'] for x in files]})
    validation=json.loads(receipt.read_text());assert validation['parent_sha256']==[x['sha256'] for x in files]
    record_acquisition(key,'pair_validation',validation)
    return [DATA/f['path'] for f in files]


def containers(key,case):
    urls=dict(re.findall(r'^(?:URL|DOCKER)_([^ ]+) := (\S+)',(UPSTREAM/'containers/Makefile').read_text(),re.M))
    records=[]
    for tool in case.get('additional_containers',[]):
        url=urls[tool];assert not url.startswith('docker://'),'OCI acquisition needs an explicit pinned receipt'
        records.append({'tool':tool,**download(url,CONTAINERS/(tool+'.sif'))})
    record_acquisition(key,'additional_containers',records)


def reference(key,case):
    accession=case['reference'];root=DATA/'datasets/ncbi/bacterial-references'/accession
    for d in ['raw','derived','metadata']:(root/d).mkdir(parents=True,exist_ok=True)
    url='https://api.ncbi.nlm.nih.gov/datasets/v2/genome/accession/'+accession+'/dataset_report'
    info=metadata(url,root/'metadata/assembly.json')['reports'][0]
    assembly=info['assembly_info']['assembly_name'].replace(' ','_')
    number=accession.split('_')[1].split('.')[0]
    base='https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/'+'/'.join(number[n:n+3] for n in range(0,9,3))+'/'+accession+'_'+assembly+'/'
    download(base+'md5checksums.txt',root/'metadata/md5checksums.txt')
    expected={x.split()[-1].removeprefix('./'):x.split()[0] for x in (root/'metadata/md5checksums.txt').read_text().splitlines()}
    records=[]
    for suffix,outname in [('genomic.fna.gz',accession+'.fasta'),('genomic.gff.gz',accession+'.gff')]:
        filename=accession+'_'+assembly+'_'+suffix
        records.append(download(base+filename,root/'raw'/filename,expected_md5=expected[filename]))
        out=root/'derived'/outname
        if not out.exists():
            with gzip.open(root/'raw'/filename,'rb') as source,out.open('wb') as target:shutil.copyfileobj(source,target)
    fasta=root/'derived'/(accession+'.fasta')
    for output,command in [(Path(str(fasta)+'.fai'),execute('samtools.sif','samtools','faidx',fasta)),
        (Path(str(fasta)+'.bwt'),execute('bwakit.sif','bwa','index',fasta))]:
        if not output.exists():
            with (case_dir(key)/('reference-'+output.suffix+'.log')).open('w') as log:
                subprocess.run(command,env=env(),stdout=log,stderr=subprocess.STDOUT,check=True)
    link(ASSETS/'genomes'/case['reference_species_dir'],root/'derived')
    # Flat read-only serving root with real files, separate from credentials.
    import os
    for path in [fasta,Path(str(fasta)+'.fai')]:
        target=HUB/'references'/path.name
        if not target.exists():os.link(path,target)
    record_acquisition(key,'reference',{'accession':accession,'metadata_url':url,'files':records,
        'derived_path':str((root/'derived').relative_to(DATA)),
        'derived_files':{p.name:hashes(p) for p in [fasta,Path(str(fasta)+'.fai'),root/'derived'/(accession+'.gff')]}})


def schema(key,case):
    species=case['reference_species_dir'];schema_id=case['schema_id']
    root=DATA/'datasets/cgmlst-org'/species/('schema-'+schema_id+'-snapshot-2026-11-08')
    for d in ['raw','derived','metadata']:(root/d).mkdir(parents=True,exist_ok=True)
    url='https://www.cgmlst.org/ncs/schema/'+schema_id+'/alleles'
    archive=root/'raw'/('cgmlst_schema_'+case['schema_name']+'_'+schema_id+'.zip')
    receipt=download(url,archive)
    extracted=root/'derived/extracted'
    if not extracted.exists():
        extracted.mkdir()
        with zipfile.ZipFile(archive) as source:source.extractall(extracted)
    fasta=list(extracted.rglob('*.fasta'));assert fasta,'Schema archive has no FASTA loci'
    parents={p.parent for p in fasta};assert len(parents)==1,parents
    raw_schema=next(iter(parents));prepared=root/'derived/prepared'
    training_root=DATA/'datasets/chewbbaca/prodigal-training-files/3.5.4'
    training=training_root/'raw'/case['training_file']
    trn=download('https://raw.githubusercontent.com/B-UMMI/chewBBACA/v3.5.4/CHEWBBACA/prodigal_training_files/'+case['training_file'],training)
    marker=root/'metadata/preparation.json'
    if not marker.exists():
        command=execute('chewbbaca.sif','chewie','PrepExternalSchema','-g',raw_schema,'-o',prepared,'--ptf',training,'--cpu','2')
        with (case_dir(key)/'schema-preparation.log').open('w') as log:
            subprocess.run(command,env=env(),stdout=log,stderr=subprocess.STDOUT,check=True)
        if not (prepared/case['training_file']).exists():shutil.copy2(training,prepared/case['training_file'])
        write(marker,{'prepared_at_utc':now(),'parent_archive_sha256':receipt['sha256'],'command':command,'raw_loci_files':len(fasta)})
    working=case_dir(key)/'inputs/schema'
    if not working.exists():shutil.copytree(prepared,working)
    bed=UPSTREAM/'assets/cgmlst'/species/'bed'/(case['reference']+'.bed')
    link(ASSETS/'cgmlst'/species/'bed'/bed.name,bed)
    record_acquisition(key,'schema',{'source':receipt,'preparation':json.loads(marker.read_text()),'training':trn,
        'prepared_path':str(prepared.relative_to(DATA)),'case_working_copy':str(working.relative_to(DATA)),
        'bed_parent_commit':PIN,'bed_sha256':hashes(bed)['sha256']})


def main(key):
    if not cases().get('sequence_processing_enabled',False):
        raise RuntimeError('Sequence-processing expansion is stopped for this run after the reported content restriction; existing results and acquisitions are preserved')
    initialize();case=cases()['cases'][key];assert case['mode']=='native'
    directory=case_dir(key);directory.mkdir(parents=True,exist_ok=True)
    status=directory/'preparation-status.json';state={'status':'RUNNING','started_at_utc':now(),'case':key}
    write(status,state)
    try:
        paths=reads(key,case);containers(key,case);reference(key,case);schema(key,case)
        with (directory/'samples.csv').open('w',newline='') as handle:
            writer=csv.writer(handle);writer.writerow(['id','platform','sequencing_run','clarity_sample_id','read1','read2','sample_name'])
            writer.writerow([case['external_id'],'illumina','PUBLIC_'+case['accession'],case['lims_id'],*map(str,paths),case['sample_name']])
        state.update(status='COMPLETE',finished_at_utc=now());write(status,state)
        print('Case prepared: '+key,flush=True)
    except Exception as error:
        state.update(status='FAILED',finished_at_utc=now(),error=str(error));write(status,state);raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('case');main(parser.parse_args().case)
