#!/usr/bin/env python3
"""Prepare and verify the one-line SDK correction for read-pair count units."""
import io
import json
from pathlib import Path
import subprocess
import tarfile
from common import DATA, RUN, REPO, now, write


def main():
    repo=Path('/home/jakob/src/codex/bonsai/bonsai-sdk');base='5789a9c7530407683f1fee9ffa450512269e62bc'
    branch='pr/parser-read-pair-count';root=DATA/'environments/sdk-read-pair-count';destination=root/'candidate'
    relative='src/bonsai_libs/parse/parsers/post_align_qc.py'
    if not destination.exists():
        root.mkdir(parents=True,exist_ok=True)
        subprocess.run(['git','-C',str(repo),'worktree','add','-b',branch,str(destination),base],check=True)
        path=destination/relative;text=path.read_text();old='            n_read_pairs=n_read_pairs,'
        assert text.count(old)==1;path.write_text(text.replace(old,'            n_read_pairs=n_read_pairs // 2,'))
        test=destination/'tests/parse/parsers/test_samtools_qc.py'
        test.write_text(test.read_text().replace('assert qc.n_read_pairs == 38702','assert qc.n_read_pairs == 19351'))
        subprocess.run(['git','-C',str(destination),'add',relative,str(test)],check=True)
        subprocess.run(['git','-C',str(destination),'commit','-m','fix: Count samtools paired reads in read pairs'],check=True)
    head=subprocess.check_output(['git','-C',str(destination),'rev-parse','HEAD'],text=True).strip()
    baseline=root/'baseline'
    if not baseline.exists():
        baseline.mkdir()
        raw=subprocess.check_output(['git','-C',str(repo),'archive',base,'src'])
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:archive.extractall(baseline,filter='data')
    checks=[]
    for name,tree,expected in [('baseline',baseline,1),('candidate',destination,0)]:
        command=['docker','run','--rm','--pull','never','--network','none','--user','1000:1000',
            '-v',str(tree/'src')+':/sdk:ro','-v',str(REPO/'scripts/jasen_pilot/check_read_pair_count.py')+':/tests/test_count.py:ro',
            '-v',str(Path.home()/'data/codex/bonsai/environments/general-test-deps')+':/test-deps:ro',
            '-e','PYTHONPATH=/sdk:/test-deps','--entrypoint','python','bonsai-species-test-api','-m','pytest','-q',
            '-p','no:cacheprovider','/tests/test_count.py']
        log=RUN/'bonsai'/('read-pair-count-'+name+'.log')
        with log.open('w') as output:result=subprocess.run(command,stdout=output,stderr=subprocess.STDOUT)
        assert result.returncode==expected,(name,result.returncode,log)
        checks.append({'tree':name,'return_code':result.returncode,'log':str(log),'command':command})
    changes=subprocess.check_output(['git','-C',str(destination),'diff','--numstat',base,head],text=True).strip()
    write(RUN/'bonsai/read-pair-count-fix.json',{'id':'SAMTOOLS-READ-PAIR-COUNT','apparent_priority':'P1',
        'branch':branch,'head':head,'base_commit':base,'repository':str(repo),'candidate':str(destination),
        'prepared_at_utc':now(),'changes':changes,'production_scope':'One integer conversion; two existing test expectations updated',
        'normal_trigger':'Every paired input using samtools stats, including the normal JASEN Illumina path',
        'observed_input_pairs':1250000,'observed_original_display':2500000,
        'upstream_units':'https://www.htslib.org/doc/1.17/samtools-stats.html',
        'validation':'Four generic count cases passed; baseline reproduced three failures and one unpaired pass',
        'checks':checks,'published':False})
    print(branch+' '+head[:10]+' verified: four generic count cases')


if __name__=='__main__':main()
