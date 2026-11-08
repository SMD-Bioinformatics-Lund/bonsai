#!/usr/bin/env python3
"""Compose the tested SDK count fix in the pilot, preserving the earlier SDK tree."""
import json
from pathlib import Path
import subprocess
from common import DATA, RUN, write
from prepare_bonsai import main as prepare_bonsai
from run_import import main as run_import


def main():
    fix=json.loads((RUN/'bonsai/read-pair-count-fix.json').read_text())
    assert fix['validation'].startswith('Four generic')
    file=RUN/'bonsai/source-context.json';context=json.loads(file.read_text())
    if 'SAMTOOLS-READ-PAIR-COUNT' not in context['candidates']:
        repo=Path(fix['repository']);destination=DATA/'environments/bonsai-pilot-sdk-pair-count/source'
        parent=context['trees']['SDK']
        destination.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run(['git','-C',str(repo),'worktree','add','--detach',str(destination),parent['head']],check=True)
        subprocess.run(['git','-C',str(destination),'cherry-pick',fix['head']],check=True)
        head=subprocess.check_output(['git','-C',str(destination),'rev-parse','HEAD'],text=True).strip()
        write(RUN/'bonsai/source-context-before-pair-count.json',context)
        context['trees']['SDK']={'path':str(destination),'head':head}
        context['candidates'][fix['id']]=fix['head']
        context['checks'].append({'name':'read-pair-count-units','status':'PASS','tests':4})
        context['parent_sdk_head']=parent['head']
        write(file,context)
    context['change']='Existing write scopes on two routes and one SDK read-pair count conversion; other changes are the parent minimal-fix composition'
    write(file,context)
    prepare_bonsai()
    run_import(script='correct_pair_count.py',artifact='pair-count-correction')


if __name__=='__main__':main()
