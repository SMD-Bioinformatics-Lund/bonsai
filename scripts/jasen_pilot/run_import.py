#!/usr/bin/env python3
"""Launch the production manifest uploader inside the isolated pilot network."""
import argparse
import os
from common import DATA, RUN, REPO, now, write
from prepare_bonsai import compose
import subprocess


def main(accounts_only=False,script='import_results.py',artifact='import'):
    command=compose('run','--rm','--no-deps','-T','--user',f'{os.getuid()}:{os.getgid()}',
        '-v',str(DATA)+':'+str(DATA)+':ro',
        '-v',str(RUN/'bonsai')+':'+str(RUN/'bonsai')+':rw',
        '-v',str(REPO)+':'+str(REPO)+':ro',
        '-v',str(DATA/'environments/prp-2.0.0/source')+':/pilot-prp:ro',
        '-e','PYTHONPATH=/pilot-prp:/app/api','-e','JASEN_PILOT_DATA='+str(DATA),
        'api','python',str(REPO/'scripts/jasen_pilot'/script))
    if accounts_only:command.append('--accounts-only')
    write(RUN/'bonsai'/(artifact+'-command.json'),{'command':command,'created_at_utc':now()})
    with (RUN/'bonsai'/(artifact+'.log')).open('a') as out:subprocess.run(command,stdout=out,stderr=subprocess.STDOUT,check=True)
    print('Pilot account setup completed' if accounts_only else 'Pinned PRP import completed',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--accounts-only',action='store_true')
    main(parser.parse_args().accounts_only)
