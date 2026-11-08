#!/usr/bin/env python3
"""Prepare a separate minimal local fix for the newly observed index-write boundary."""
import ast
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
from common import DATA, RUN, now, write

REPOSITORY=Path('/home/jakob/src/codex/bonsai')
BRANCH='pr/index-write-authentication'
BASE='pr/account-role-permissions'
PATH='api/bonsai_api/routers/samples/sample_analysis.py'


def git(*args,input=None,env=None):return subprocess.check_output(['git','-C',str(REPOSITORY),*args],input=input,text=True,env=env).strip()


def main():
    base=git('rev-parse',BASE);text=git('show',base+':'+PATH)+'\n'
    original=text
    text=text.replace('from .permissions import READ_PERMISSION','from .permissions import READ_PERMISSION, WRITE_PERMISSION')
    for name in ['create_genome_signatures_sample','add_ska_index_to_sample']:
        node=next(n for n in ast.walk(ast.parse(text)) if isinstance(n,ast.AsyncFunctionDef) and n.name==name)
        old=ast.get_source_segment(text,node)
        marker='    db: Database = Depends(get_database),'
        assert old.count(marker)==1
        new=old.replace(marker,marker+'\n    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument\n        get_current_active_user, scopes=[WRITE_PERMISSION]\n    ),')
        text=text.replace(old,new)
    ast.parse(text)
    receipt=RUN/'bonsai/index-auth-fix.json'
    old=subprocess.run(['git','-C',str(REPOSITORY),'show-ref','--verify','--hash','refs/heads/'+BRANCH],capture_output=True,text=True)
    previous=old.stdout.strip() if old.returncode==0 else None
    if previous:assert receipt.exists() and json.loads(receipt.read_text())['head']==previous
    fd,index=tempfile.mkstemp(dir=DATA/'tmp/reference-pilot',prefix='auth-index-');os.close(fd);os.unlink(index)
    environment=dict(os.environ,GIT_INDEX_FILE=index)
    try:
        git('read-tree',base,env=environment)
        blob=git('hash-object','-w','--stdin',input=text)
        git('update-index','--cacheinfo','100644,'+blob+','+PATH,env=environment)
        tree=git('write-tree',env=environment)
    finally:
        if Path(index).exists():Path(index).unlink()
    if previous and git('rev-parse',previous+'^{tree}')==tree:head=previous
    else:
        head=git('commit-tree',tree,'-p',base,input='fix: Require write permission for index and signature uploads\n\nFinding: INDEX-WRITE-AUTHENTICATION\nTwo mutation routes lacked authentication and role checks.\n')
        git('update-ref','refs/heads/'+BRANCH,head,previous or '0'*40)
    changes=git('diff','--numstat',base,head)
    if previous==head:
        print(BRANCH+' '+head[:10]+' unchanged; existing validation retained')
        return
    source=DATA/'environments/index-write-auth-check'/head[:10]
    for label,revision in [('baseline',base),('candidate',head)]:
        destination=source/label
        if not destination.exists():
            destination.mkdir(parents=True)
            raw=subprocess.check_output(['git','-C',str(REPOSITORY),'archive',revision,'api/bonsai_api'])
            with tarfile.open(fileobj=io.BytesIO(raw)) as archive:archive.extractall(destination,filter='data')
    write(receipt,{'id':'INDEX-WRITE-AUTHENTICATION','apparent_priority':'P0','branch':BRANCH,'head':head,'base_ref':BASE,'base_commit':base,
        'production_changes':changes,'source_snapshots':str(source),'created_at_utc':now(),'validation':'pending',
        'normal_trigger':'Direct API use without authentication or with an ordinary account; normal authorized ingestion is unaffected.',
        'minimal_fix':'Use the existing write scope on the two mutation routes; no storage or parser change.',
        'dependency':'ACCOUNT-ROLE-PERMISSIONS','no_live_records_modified_by_probe':True,'published':False})
    print(BRANCH+' '+head[:10]+' '+changes)


if __name__=='__main__':main()
