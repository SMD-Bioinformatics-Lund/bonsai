#!/usr/bin/env python3
"""Acquire only containers used by the Illumina E. coli pilot, not all JASEN tools."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import subprocess
from common import DATA, RUN, SOURCE, CONTAINERS, download, env, hashes, now, write

TOOLS=['ncbi-amrfinderplus','blast','bwakit','chewbbaca','fastqc','freebayes','gambitcore','htslib',
       'jasentool','mlst','perl-json','plasmidfinder','prodigal','quast','resfinder','samtools','seqtk',
       'serotypefinder','shigatyper','ska2','skesa','sourmash','virulencefinder']


def main():
    text=(SOURCE/'containers/Makefile').read_text()
    urls=dict(re.findall(r'^(?:URL|DOCKER)_([^ ]+) := (\S+)',text,re.M))
    CONTAINERS.mkdir(parents=True,exist_ok=True)
    def one(name):
        target=CONTAINERS/(name+'.sif');url=urls[name]
        if url.startswith('docker://'):
            receipt=CONTAINERS/'metadata'/(name+'.sif.receipt.json')
            if not target.exists():
                print('Pulling '+name,flush=True)
                with (RUN/('container-'+name+'.log')).open('w') as log:
                    subprocess.run(['singularity','pull',str(target),url],env=env(),stdout=log,stderr=subprocess.STDOUT,check=True)
            previous=json.loads(receipt.read_text()) if receipt.exists() else None
            record={'url':url,'path':str(target.relative_to(DATA)),**hashes(target),'acquired_at_utc':previous['acquired_at_utc'] if previous else now(),'publisher_checksum_verified':False}
            if previous:assert previous['sha256']==record['sha256']
            write(receipt,record)
        else:
            if name=='seqtk' and (DATA/'environments/seqtk-1.4.sif').exists() and not target.exists():
                target.symlink_to(DATA/'environments/seqtk-1.4.sif')
            record=download(url,target)
        print('Container ready: '+name,flush=True)
        return {'tool':name,**record}
    with ThreadPoolExecutor(max_workers=3) as pool:records=list(pool.map(one,TOOLS))
    write(RUN/'containers.json',{'upstream_commit':'e5e86ca8d87ec8173b6a245135b5a1858c771a5d','containers':records})
    print('All '+str(len(records))+' required containers ready')


if __name__=='__main__':main()
