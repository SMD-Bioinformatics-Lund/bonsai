#!/usr/bin/env python3
"""Prepare pinned public reference assets for the benign K-12 software pilot."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import gzip
import io
import json
import re
import shutil
import tarfile
import urllib.request
from common import DATA, RUN, SOURCE, CONTAINERS, ASSETS, PIN, download, env, execute, hashes, link, now, run, write


def make_dirs(path):
    for part in ['raw','derived','metadata']:(path/part).mkdir(parents=True,exist_ok=True)


def cge(name,version):
    path=DATA/'datasets/cge'/name/version;make_dirs(path)
    record=download(f'https://bitbucket.org/genomicepidemiology/{name}/get/{version}.tar.gz',path/'raw'/(version+'.tar.gz'))
    destination=path/'derived'/name
    if not destination.exists():
        destination.mkdir()
        with tarfile.open(path/'raw'/(version+'.tar.gz')) as archive:
            members=archive.getmembers()
            for member in members:
                parts=member.name.split('/',1)
                if len(parts)==1:continue
                member.name=parts[1]
                archive.extract(member,destination,filter='data')
    # Upstream runtime records database identity from VERSION; retain the
    # release explicitly when the publisher archive has no Git metadata.
    if not (destination/'VERSION').exists():(destination/'VERSION').write_text(version+'\n')
    link(name,destination)
    return {'provider':'CGE','dataset':name,'release':version,'files':[record],'derived_path':str(destination.relative_to(DATA))}


def gambit():
    path=DATA/'datasets/gambit/refseq-curated/1.0';make_dirs(path);records=[]
    for extension in ['gdb','gs']:
        name='gambit-refseq-curated-1.0.'+extension
        url='https://storage.googleapis.com/jlumpe-gambit/public/databases/refseq-curated/1.0/'+name
        with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=40) as response:
            header=dict(response.headers);checksum=','.join(response.headers.get_all('x-goog-hash',[]))
            size=int(response.headers['Content-Length'])
        md5_b64=re.search(r'md5=([^,]+)',checksum).group(1)
        expected=base64.b64decode(md5_b64).hex()
        write(path/'metadata'/(name+'.headers.json'),header)
        records.append(download(url,path/'raw'/name,expected_md5=expected,expected_bytes=size))
    working=path/'derived/database'
    if not working.exists():shutil.copytree(path/'raw',working)
    asset=ASSETS/'gambit_db'
    if asset.is_symlink() and asset.resolve()==(path/'raw').resolve():asset.unlink()
    link('gambit_db',working)
    return {'provider':'GAMBIT','dataset':'refseq-curated','release':'1.0','files':records,'derived_path':str(working.relative_to(DATA))}


def reference():
    accession='GCF_000005845.2';directory=accession+'_ASM584v2'
    path=DATA/'datasets/ncbi/k12-mg1655-reference'/accession;make_dirs(path)
    base='https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/005/845/'+directory+'/'
    download(base+'md5checksums.txt',path/'metadata/md5checksums.txt')
    expected={line.split()[-1].removeprefix('./'):line.split()[0] for line in (path/'metadata/md5checksums.txt').read_text().splitlines()}
    records=[]
    for suffix,output in [('genomic.fna.gz',accession+'.fasta'),('genomic.gff.gz',accession+'.gff')]:
        filename=directory+'_'+suffix
        records.append(download(base+filename,path/'raw'/filename,expected_md5=expected[filename]))
        target=path/'derived'/output
        if not target.exists():
            with gzip.open(path/'raw'/filename,'rb') as source,target.open('wb') as out:shutil.copyfileobj(source,out)
    target=path/'derived'
    link('genomes/escherichia_coli',target)
    bed=ASSETS/'wgmlst/escherichia_coli/bed';bed.mkdir(parents=True,exist_ok=True)
    filename=accession+'.bed';parent=SOURCE/'assets/wgmlst/escherichia_coli/bed'/filename
    if not (bed/filename).exists():shutil.copy2(parent,bed/filename)
    write(path/'metadata/derivation.json',{'reference':accession,'decompression':'gzip','derived':{name:hashes(target/name) for name in [accession+'.fasta',accession+'.gff']},'bed':{'parent_repository':'https://github.com/genomic-medicine-sweden/jasen','parent_commit':PIN,'path':'assets/wgmlst/escherichia_coli/bed/'+filename,'sha256':hashes(parent)['sha256']}})
    return {'provider':'NCBI','dataset':'k12-mg1655-reference','release':accession,'files':records,'derived_path':str(target.relative_to(DATA))}


def amrfinder():
    version='2026-10-29.1';path=DATA/'datasets/ncbi/amrfinderplus'/version;make_dirs(path)
    base='https://ftp.ncbi.nlm.nih.gov/pathogen/Antimicrobial_resistance/AMRFinderPlus/database/4.2/'+version+'/'
    with urllib.request.urlopen(base,timeout=40) as response:index=response.read().decode()
    (path/'metadata/publisher-index.html').write_text(index)
    names=[name for name in re.findall(r'href="([^"]+)"',index) if '/' not in name and re.fullmatch(r'[A-Za-z0-9_.-]+',name)]
    assert 'version.txt' in names and 'AMR.LIB' in names
    with ThreadPoolExecutor(max_workers=3) as pool:records=list(pool.map(lambda name:download(base+name,path/'raw'/name),names))
    assert (path/'raw/version.txt').read_text().strip()==version
    destination=path/'derived/database'
    if not destination.exists():shutil.copytree(path/'raw',destination)
    link('amrfinder_db/latest',destination)
    return {'provider':'NCBI','dataset':'AMRFinderPlus','release':version,'database_format':'4.2','files':records,'derived_path':str(destination.relative_to(DATA))}


def acquire():
    jobs=[('resfinder_db','2.6.0'),('pointfinder_db','4.1.1'),('virulencefinder_db','2.0.1'),('serotypefinder_db','1.1.0'),('plasmidfinder_db','2.2.0')]
    functions=[lambda n=n,v=v:cge(n,v) for n,v in jobs]+[gambit,reference,amrfinder]
    with ThreadPoolExecutor(max_workers=3) as pool:records=list(pool.map(lambda f:f(),functions))
    target=DATA/'datasets/ena/k12-mg1655/ERR022075/metadata'
    write(RUN/'reference-assets.json',{'acquired_at_utc':now(),'upstream_commit':PIN,'datasets':records})
    catalog=DATA/'datasets/catalogs'
    catalog.mkdir(parents=True,exist_ok=True)
    write(catalog/'2026-11-08-k12-assets.json',{'datasets':records})
    source=__import__('pathlib').Path(__file__).resolve().parents[2]/'datasets/jasen_pilot_assets.json'
    write(source,{'data_root':str(DATA),'datasets':records})


def index_assets():
    for name in ['resfinder_db','pointfinder_db','virulencefinder_db','serotypefinder_db','plasmidfinder_db']:
        destination=(ASSETS/name).resolve();marker=destination/'.pilot-index-complete.json'
        if marker.exists():continue
        command=execute('virulencefinder.sif','python3',str(destination/'INSTALL.py'),'kma_index')
        # INSTALL.py uses the working directory to locate its FASTA files.
        import subprocess
        with (RUN/('index-'+name+'.log')).open('w') as output:
            subprocess.run(command,cwd=destination,env=env(),stdout=output,stderr=subprocess.STDOUT,check=True)
        write(marker,{'at':now(),'command':command,'parent':str(destination.parent.parent/'raw')})
        print('Indexed '+name,flush=True)
    reference=(ASSETS/'genomes/escherichia_coli').resolve();fasta=reference/'GCF_000005845.2.fasta'
    if not fasta.with_suffix('.fasta.fai').exists():run(execute('samtools.sif','samtools','faidx',fasta),RUN/'reference-faidx.log')
    if not fasta.with_suffix('.fasta.bwt').exists():run(execute('bwakit.sif','bwa','index',fasta),RUN/'reference-bwa-index.log')
    db=(ASSETS/'amrfinder_db/latest').resolve();marker=db/'.pilot-index-complete.json'
    if not marker.exists():
        command=execute('ncbi-amrfinderplus.sif','amrfinder_index',db)
        run(command,RUN/'index-amrfinder.log');write(marker,{'at':now(),'command':command})
    print('Reference indexes ready',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=['download','index']);args=parser.parse_args()
    if args.stage=='download':acquire()
    else:index_assets()
