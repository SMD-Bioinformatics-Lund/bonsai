#!/usr/bin/env python3
"""Continue automatically from pipeline completion through import and browser checks."""
import json
from pathlib import Path
import subprocess
import time
from common import DATA, RUN, REPO, now, write


def main():
    file=RUN/'pilot-status.json'
    state={'status':'RUNNING','stage':'waiting-for-upstream-pipeline','started_at_utc':now(),
        'scope':'Public MG1655 reference-strain software integration pilot',
        'dataset':'ERR022075','pipeline_status':str(RUN/'pipeline-status.json')}
    write(file,state)
    try:
        while True:
            pipeline=json.loads((RUN/'pipeline-status.json').read_text())
            if pipeline['status']=='COMPLETE':break
            if pipeline['status']=='FAILED':raise RuntimeError('Upstream pipeline failed; see pipeline-status.json and pipeline.stdout.log')
            time.sleep(10)
        state['stage']='pilot-index-write-authorization';write(file,state)
        subprocess.run(['/usr/bin/python3',str(REPO/'scripts/jasen_pilot/activate_auth_fix.py')],cwd=REPO,check=True)
        state['stage']='official-prp-import';write(file,state)
        subprocess.run(['/usr/bin/python3',str(REPO/'scripts/jasen_pilot/run_import.py')],cwd=REPO,check=True)
        state['stage']='native-qc-count-correction';write(file,state)
        subprocess.run(['/usr/bin/python3',str(REPO/'scripts/jasen_pilot/activate_pair_count_fix.py')],cwd=REPO,check=True)
        state['stage']='ordinary-user-browser';write(file,state)
        python=Path.home()/'data/codex/bonsai/environments/release-test/bin/python'
        subprocess.run([str(python),str(REPO/'scripts/jasen_pilot/check_browser.py')],cwd=REPO,check=True)
        state['stage']='literal-result-fidelity';write(file,state)
        subprocess.run([str(python),str(REPO/'scripts/jasen_pilot/check_result_fidelity.py')],cwd=REPO,check=True)
        imported=json.loads((RUN/'bonsai/import-status.json').read_text())
        browser=json.loads((RUN/'bonsai/browser-status.json').read_text())
        assert imported['status']=='COMPLETE' and browser['status']=='COMPLETE'
        assert all(row['status']=='PASS' for row in browser['checks'])
        state.update(status='COMPLETE',stage='complete',finished_at_utc=now(),sample_id=imported['sample_id'],
            analyses_stored=imported['analysis_records'],browser_checks=len(browser['checks']),
            frontend='http://100.90.51.21:18100',record='http://100.90.51.21:18100/sample/'+imported['sample_id'],
            limitations=['One laboratory reference strain and one paired Illumina input',
                'Bundled MLST database snapshot; no claim of matching the deployment database snapshots',
                'No clinical validation or decision submission; one-control automatic similarity widget only',
                'Local minimal JASEN, application and SDK patches are active'],
            credentials_file=str(RUN/'bonsai/accounts.json'))
        write(file,state)
        print('Producer-to-browser pilot completed; local results and screenshots saved',flush=True)
    except Exception as error:
        state.update(status='FAILED',finished_at_utc=now(),error=str(error));write(file,state);raise


if __name__=='__main__':main()
