#!/usr/bin/env python3
"""Run focused checks against each isolated local PR's source tree.

The reusable audit harness stays on the combined test branch; product branches
contain only their issue-scoped production changes. Containers have no network.
All snapshots, logs and dependencies remain on the external data drive.
"""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile

REPO=Path(__file__).resolve().parents[1]
DATA=Path.home()/'data/codex/bonsai'
ROOT=DATA/'runs/2026-11-06-species-ui/minimal-prs/2026-11-08'
SDK_BASE='5789a9c7530407683f1fee9ffa450512269e62bc'
EXTRA='minimal_pr_extra_checks.py'

# Each selection exercises the reported behavior, not unrelated fixes that happen
# to share an older test module. Transport/curation work is always stubbed.
CASES={
 'ORDINARY-RECORD-DELETE':[('api','test_bounded_record_workflows.py','record_deletion_requires_write_permission')],
 'ACCOUNT-ROLE-PERMISSIONS':[('api','test_account_permissions.py','generic_record_creation or write_only_role'),('api',EXTRA,'ordinary_legacy_list')],
 'ANALYSIS-UPLOAD-ROLE-GATE':[('permission',None,None)],
 'PRIVATE-RECORD-SCOPE':[('api',EXTRA,'private_creation')],
 'GROUP-DELETE-MEMBERSHIP-LOSS':[('api','test_general_ui_regressions.py','group_lookup')],
 'GROUP-MEMBERSHIP-LOSS':[('node','test_group_memberships.cjs','unchanged common|deselecting a common|adding a common|changing selection during Apply')],
 'GROUP-MEMBERSHIP-LIMIT':[('node','test_group_memberships.cjs','lookup chunks|empty membership')],
 'METADATA-ADD-500':[('api','test_general_ui_regressions.py','appending_metadata or duplicate_metadata')],
 'RECOVERY-METADATA-LOSS':[('api','test_save_recovery.py','simultaneous_independent_metadata or simultaneous_duplicate_field')],
 'METADATA-CATEGORY-LOSS':[('frontend','test_general_ui_regressions.py','noncontiguous_metadata')],
 'METADATA-TABLE-EMPTY':[('api','test_general_ui_regressions.py','stored_metadata_reads'),('frontend','test_general_ui_regressions.py','metadata_table_is_rendered')],
 'CSV-EMPTY-CELL-500':[('api',EXTRA,'csv_missing_numeric')],
 'RECOVERY-COMMENT-IDENTITIES':[('api','test_save_recovery.py','simultaneous_comments_have_distinct_ids')],
 'RECOVERY-COMMENT-RETRY':[('api','test_save_recovery.py','concurrent_replay or replay_with_changed or request_keys_are_scoped'),('api',EXTRA,'comment_header'),('frontend',EXTRA,'comment_recovery or context_free_comment')],
 'RECOVERY-GROUP-OVERLAP':[('node','test_save_recovery.cjs','stale editor sends only')],
 'ADMIN-CREATE-USER-500':[('frontend','test_general_ui_regressions.py','new_user_accepts')],
 'ADMIN-EDIT-USER-500':[('frontend','test_general_ui_regressions.py','edit_form_accepts'),('api','test_general_ui_regressions.py','profile_update_returns')],
 'PRIVATE-GROUP-INVITE-500':[('api','test_general_ui_regressions.py','private_group')],
 'PENDING-SAMPLE-500':[('frontend','test_general_ui_regressions.py','pending_sample_summary')],
 'TB-CURATION-500':[('frontend','test_bounded_record_workflows.py','optional_stored_curation')],
 'TB-NO-AMR-500':[('frontend','test_bounded_record_workflows.py','stored_null_result'),('frontend',EXTRA,'null_detail')],
 'VARIANT-FILTER-AND':[('frontend','test_readonly_details.py','numeric_filters_require')],
 'VARIANT-HIDE-DISMISSED-500':[('frontend','test_readonly_details.py','hide_dismissed_uses')],
 'ECOLI-VARIANTS-EMPTY':[('frontend',EXTRA,'unsupported_view')],
 'CURATION-DOUBLE-SUBMIT':[('frontend',EXTRA,'single_confirmation or confirmation_renders')],
 'EMM-DISPLAY-MISSING':[('frontend','test_parser_display.py','current_emm_descriptor')],
 'DISPLAY-EXTENDED-CONTEXT':[('frontend','test_parser_display.py','extended_summary_imports')],
 'DISPLAY-EMM-TABLE':[('mongo',EXTRA,'emm_projection')],
 'EMM-LIMS-EXPORT-500':[('api','test_readonly_exports.py','emm_export')],
 'KLEBORATE-UPLOAD-422':[('api',EXTRA,'kleborate_route or kleborate_service')],
 'KLEBORATE-CLIENT-COMPANION':[('sdk',EXTRA,'sdk_companion')],
 'PARSER-MYKROBE-SELECTION':[('sdk','test_fidelity_regressions.py','mykrobe_selected')],
 'PARSER-BRACKEN-EMPTY':[('sdk','test_fidelity_regressions.py','header_only_bracken')],
 'PARSER-COVERAGE-STREAM':[('sdk','test_fidelity_regressions.py','samtools_coverage')],
 # Real Chromium/DataTables checks are run by the browser companion harness.
 'QC-FILTER-EMPTY':[], 'SELECTED-FILTER-STALE':[], 'VARIANT-SELECT-ALL-INVALID':[],
 'BASKET-UNDEFINED-ASSAY':[('node','test_basket.cjs','record names remain literal')],
 'ACCOUNT-STALE-PAGES':[('node','test_minimal_account_state.cjs','account state')],
}


def extract(repo,head,target,paths):
    if target.exists():return
    target.mkdir(parents=True)
    payload=subprocess.check_output(['git','-C',str(repo),'archive',head,*paths])
    with tarfile.open(fileobj=io.BytesIO(payload)) as archive:archive.extractall(target,filter='data')


def snapshot(candidate):
    destination=ROOT/'snapshots'/candidate['id']/candidate['head'][:10]
    if candidate['repository']=='SDK':
        extract(REPO/'bonsai-sdk',candidate['head'],destination,['src/bonsai_libs'])
    else:
        extract(REPO,candidate['head'],destination,['api/bonsai_api','frontend/bonsai_app','frontend/web/js'])
    return destination


def prepare_checks(destination,case,kind):
    testdir=destination/('checks-'+kind);testdir.mkdir(exist_ok=True)
    if kind in {'api','frontend','mongo'}:
        for name in ['test_general_ui_regressions.py','test_bounded_record_workflows.py','test_save_recovery.py']:
            shutil.copy2(REPO/('api' if kind=='mongo' else kind)/'tests'/name,testdir/name)
        if kind in {'api','mongo'}:
            shutil.copy2(REPO/'api/tests/test_account_permissions.py',testdir/'test_account_permissions.py')
            shutil.copy2(REPO/'api/tests/lims_export/test_readonly_details.py',testdir/'test_readonly_exports.py')
        else:
            for name in ['test_readonly_details.py','test_parser_display.py','conftest.py']:
                shutil.copy2(REPO/'frontend/tests'/name,testdir/name)
            # Other issues are checked with a valid completed pipeline so they
            # do not accidentally rely on the separate pending-record fix.
            if case!='PENDING-SAMPLE-500':
                for filename in ['test_general_ui_regressions.py','test_bounded_record_workflows.py']:
                    path=testdir/filename;text=path.read_text()
                    text=text.replace('"pipeline": None, "sequencing": None', '"pipeline": {"assay":"generic","pipeline_info":{"definition":{"name":"generic","version":"1"},"run_config":{"analysis_profile":[],"configuration_files":[]},"databases":[]}}, "sequencing": {"sequencing_run_id":"generic"}')
                    path.write_text(text)
    if kind=='sdk':
        shutil.copy2(REPO/'bonsai-sdk/tests/parse/parsers/test_fidelity_regressions.py',testdir/'test_fidelity_regressions.py')
    if kind in {'api','frontend','sdk','mongo'}:
        shutil.copy2(REPO/'scripts/minimal_pr_extra_checks.py',testdir/EXTRA)
    if kind=='node':
        testdir=destination/'frontend/tests';testdir.mkdir(exist_ok=True)
        for name in ['test_group_memberships.cjs','test_save_recovery.cjs','test_basket.cjs']:
            shutil.copy2(REPO/'frontend/tests'/name,testdir/name)
        # The literal-name check does not depend on account-scoped storage.
        path=testdir/'test_basket.cjs';text=path.read_text().replace('basket_content:test-user','basket_content')
        path.write_text(text)
        shutil.copy2(REPO/'scripts/minimal_pr_account_state.cjs',testdir/'test_minimal_account_state.cjs')
    return testdir


def check(candidate):
    case=candidate['id'];source=snapshot(candidate)
    sdk_base=ROOT/'sdk-baseline';extract(REPO/'bonsai-sdk',SDK_BASE,sdk_base,['src/bonsai_libs'])
    attempt=ROOT/'checks'/case/candidate['head'][:10]/datetime.now(timezone.utc).strftime('%H%M%S')
    attempt.mkdir(parents=True,exist_ok=True);outcomes=[]
    for n,(kind,testfile,selection) in enumerate(CASES[case]):
        testdir=prepare_checks(source,case,kind)
        image='bonsai-species-test-frontend' if kind=='frontend' else 'bonsai-general-node-tools' if kind=='node' else 'bonsai-species-test-api'
        cmd=['docker','run','--rm','--pull','never','--network','none','--user','1000:1000',
             '-v',f'{DATA}:{DATA}','-v',f'{REPO}/scripts:/audit-scripts:ro','-v',f'{source}:/candidate:ro',
             '-v',f'{DATA}/environments/general-test-deps:/test-deps:ro']
        if kind=='node':
            cmd += ['-e','NODE_PATH=/app/frontend/node_modules','--entrypoint','node',image,'--test','--test-reporter=tap',f'--test-name-pattern={selection}',f'/candidate/frontend/tests/{testfile}']
        else:
            sdk=source/'src/bonsai_libs' if candidate['repository']=='SDK' else sdk_base/'src/bonsai_libs'
            cmd += ['-v',f'{sdk}:/usr/local/lib/python3.11/site-packages/bonsai_libs:ro']
            if candidate['repository']!='SDK':
                cmd += ['-v',f'{source}/api/bonsai_api:/app/api/bonsai_api:ro','-v',f'{source}/frontend/bonsai_app:/app/frontend/bonsai_app:ro']
            cmd += ['-e','PYTHONPATH=/test-deps:/app/api:/app/frontend','-e','SECRET_KEY=isolated-release-check','-e','TESTING=true','-e','PYTHONDONTWRITEBYTECODE=1','--entrypoint','python',image]
            if kind=='permission':
                cmd += ['/audit-scripts/check_release_permission_gate.py','--output',str(attempt/'permission.json')]
            else:
                cmd += ['-m','pytest','-q','-p','no:cacheprovider',str(testdir/testfile),'-k',selection,'--confcutdir',str(testdir)]
        mongo=None
        if kind=='mongo':
            mongo=subprocess.check_output(['docker','run','-d','--rm','--pull','never','--network','none','--tmpfs','/data/db:rw,size=256m','mongo:4.4.22','--bind_ip','127.0.0.1'],text=True).strip()
            cmd[cmd.index('none')]='container:'+mongo
            cmd[cmd.index('--entrypoint'):cmd.index('--entrypoint')]=['-e','MINIMAL_AUDIT_MONGO_URI=mongodb://127.0.0.1:27017']
        try:
            result=subprocess.run(cmd,capture_output=True,text=True,timeout=90)
        finally:
            if mongo:subprocess.run(['docker','stop',mongo],capture_output=True,check=True)
        log=attempt/f'{n}-{kind}.log';log.write_text(result.stdout+result.stderr)
        ok=result.returncode==0
        passed=sum(int(x) for x in re.findall(r'(\d+) passed',result.stdout))
        if kind=='permission' and ok:
            report=json.loads((attempt/'permission.json').read_text());ok=all(x['status']=='PASS' for x in report['cases']);passed=sum(x['status']=='PASS' for x in report['cases'])
        if kind=='node':
            match=re.search(r'# pass (\d+)',result.stdout);passed=int(match.group(1)) if match else 0
        outcomes.append({'kind':kind,'status':'PASS' if ok else 'FAIL','passed':passed,'log':str(log.relative_to(ROOT)),
                         'log_sha256':sha256(log.read_bytes()).hexdigest(),'command':cmd})
        if not ok:print(f'{case} / {kind}: FAIL: {log}',flush=True)
    record={'id':case,'head':candidate['head'],'status':'PASS' if outcomes and all(x['status']=='PASS' for x in outcomes) else 'BROWSER_PENDING' if not outcomes else 'FAIL','checks':outcomes}
    (attempt/'result.json').write_text(json.dumps(record,indent=2)+'\n')
    print(f'{case}: {record["status"]} ({sum(x["passed"] for x in outcomes)} checks)',flush=True)
    return record


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--only',nargs='+');args=parser.parse_args()
    manifest=json.loads((ROOT/'branches.json').read_text());results=[]
    for candidate in manifest['candidates']:
        if args.only and candidate['id'] not in args.only:continue
        results.append(check(candidate))
    path=ROOT/('verification-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'.json');path.write_text(json.dumps(results,indent=2)+'\n')
    if any(x['status']=='FAIL' for x in results):raise SystemExit(1)
