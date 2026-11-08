#!/usr/bin/env python3
"""Package local fix branches, review bodies and measured verification metadata.

This writes local files only. Push commands are provided as text for the user;
no remote branch or PR is created. Production diffs exclude the audit harness.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shlex
import subprocess
from hashlib import sha256

from verify_minimal_prs import ROOT, REPO, CASES

OUTPUT=REPO/'docs/local-testing/minimal-prs'
TITLES={
 'ORDINARY-RECORD-DELETE':'Require write permission for record deletion',
 'ACCOUNT-ROLE-PERMISSIONS':'Apply route-specific role scopes to generic create and read',
 'ANALYSIS-UPLOAD-ROLE-GATE':'Require write permission for analysis uploads',
 'PRIVATE-RECORD-SCOPE':'Reject new private-marked records while sample ACLs are unfinished',
 'GROUP-DELETE-MEMBERSHIP-LOSS':'Limit group deletion to the target membership edges',
 'GROUP-MEMBERSHIP-LOSS':'Preserve individual memberships when applying common groups',
 'RECOVERY-METADATA-LOSS':'Append metadata atomically without overwriting concurrent fields',
 'RECOVERY-COMMENT-IDENTITIES':'Allocate distinct comment IDs under concurrent append',
 'RECOVERY-GROUP-OVERLAP':'Send only changed fields from the group editor',
 'METADATA-ADD-500':'Append typed metadata alongside existing stored fields',
 'METADATA-CATEGORY-LOSS':'Group interleaved metadata categories without dropping fields',
 'METADATA-TABLE-EMPTY':'Render accepted metadata table shapes consistently',
 'CSV-EMPTY-CELL-500':'Normalize missing numeric CSV cells to empty text',
 'CURATION-DOUBLE-SUBMIT':'Submit a confirmation once and render refreshed state',
 'RECOVERY-COMMENT-RETRY':'Deduplicate identified comment retries and preserve failed drafts',
 'SELECTED-FILTER-STALE':'Redraw selected-only tables after selection changes',
 'VARIANT-SELECT-ALL-INVALID':'Restrict bulk row selection to identified checkboxes',
 'VARIANT-FILTER-AND':'Intersect numeric row-filter predicates',
 'VARIANT-HIDE-DISMISSED-500':'Read the stored rejection decision when filtering rows',
 'QC-FILTER-EMPTY':'Use plain QC status values for SearchBuilder filtering',
 'GROUP-MEMBERSHIP-LIMIT':'Batch membership lookups within the API query limit',
 'ADMIN-CREATE-USER-500':'Handle typed SDK not-found during local user creation',
 'ADMIN-EDIT-USER-500':'Open typed account responses and preserve profile update semantics',
 'ACCOUNT-STALE-PAGES':'Revalidate restored pages after account changes',
 'BASKET-UNDEFINED-ASSAY':'Render basket names literally and absent assay as empty text',
 'PRIVATE-GROUP-INVITE-500':'Use consistent account shapes for private-group invitees',
 'PENDING-SAMPLE-500':'Render pending records without pipeline metadata',
 'TB-CURATION-500':'Render decisions without optional display metadata',
 'TB-NO-AMR-500':'Keep summary and detail available for null stored results',
 'ECOLI-VARIANTS-EMPTY':'Label the stored detail view with its supported result scope',
 'EMM-DISPLAY-MISSING':'Render current EMM descriptors and empty availability states',
 'DISPLAY-EMM-TABLE':'Project requested EMM fields from their current stored paths',
 'DISPLAY-EXTENDED-CONTEXT':'Import extended-summary cards with record context',
 'EMM-LIMS-EXPORT-500':'Read current EMM descriptors in CSV and TSV formatters',
 'KLEBORATE-UPLOAD-422':'Forward an optional hAMRonization companion through the API',
 'KLEBORATE-CLIENT-COMPANION':'Send the optional hAMRonization file in SDK multipart uploads',
 'PARSER-MYKROBE-SELECTION':'Honor selected result categories in the Mykrobe parser',
 'PARSER-BRACKEN-EMPTY':'Return an empty list for header-only Bracken reports',
 'PARSER-COVERAGE-STREAM':'Read coverage streams once and preserve every supplied row',
}
MERGE_NOTES={
 'METADATA-TABLE-EMPTY':'When combined with CSV-EMPTY-CELL-500, union the pydantic imports (BeforeValidator and field_validator).',
 'CSV-EMPTY-CELL-500':'When combined with METADATA-TABLE-EMPTY, union the pydantic imports (BeforeValidator and field_validator).',
 'TB-NO-AMR-500':'When combined with VARIANT-HIDE-DISMISSED-500, retain both the decision merge and the null-safe row lookup.',
 'VARIANT-HIDE-DISMISSED-500':'When combined with TB-NO-AMR-500, retain both the decision merge and the null-safe row lookup.',
}


def verification(candidates):
    final=[]
    browser_files=sorted((ROOT/'browser-checks').glob('*/results.json'))
    for c in candidates:
        found=[]
        for path in (ROOT/'checks'/c['id']/c['head'][:10]).glob('*/result.json'):
            record=json.loads(path.read_text())
            if record['head']==c['head']:found.append((path,record))
        if CASES[c['id']]:
            path,record=max(found,key=lambda x:x[0].stat().st_mtime_ns)
            assert record['status']=='PASS' and all(x['passed']>0 for x in record['checks']),record
            row={'id':c['id'],'head':c['head'],'status':'PASS','passed':sum(x['passed'] for x in record['checks']),
                 'method':', '.join(dict.fromkeys(x['kind'] for x in record['checks'])),
                 'result':str(path.relative_to(ROOT)),
                 'log_hashes':{x['log']:x['log_sha256'] for x in record['checks']}}
        else:
            records=[(path,row) for path in browser_files for row in json.loads(path.read_text()) if row['id']==c['id'] and row['mode']=='candidate' and row['head']==c['head']]
            path,record=max(records,key=lambda x:x[0].stat().st_mtime_ns)
            assert record['status']=='PASS' and record['passed']==record['total'],record
            row={'id':c['id'],'head':c['head'],'status':'PASS','passed':record['passed'],'method':'Chromium / real DataTables plugins',
                 'result':str(path.relative_to(ROOT)),'artifact':record['artifact']}
        final.append(row)
    result={'created_at':datetime.now(timezone.utc).isoformat(),'scope':'Isolated candidate checks, generic fixtures and literal frozen-input parser contracts; not full live ingestion or clinical validation',
            'candidate_count':len(final),'passing':len(final),'checks_passed':sum(x['passed'] for x in final),'candidates':final}
    (ROOT/'verification-final.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    manifest=json.loads((ROOT/'branches.json').read_text())
    content=json.loads((REPO/'docs/local-testing/development-review-content.json').read_text())
    assessments=json.loads((REPO/'docs/local-testing/fix-assessments.json').read_text())
    assert set(assessments['issues'])=={x['id'] for x in content['issues']}
    verified=verification(manifest['candidates']);checks={x['id']:x for x in verified['candidates']}
    issues={x['id']:x for x in content['issues']}
    integration=json.loads((ROOT/'integration/context.json').read_text())
    assert all(x['status']=='PASS' for x in integration['checks']) and len(integration['checks'])==5,integration
    assert integration['candidates']=={x['id']:x['head'] for x in manifest['candidates']}
    static=json.loads((ROOT/'integration/static-analysis.json').read_text())
    assert len(static)==2 and all(x['status']=='PASS' for x in static),static
    OUTPUT.mkdir(parents=True,exist_ok=True)
    packaged=[]
    for c in manifest['candidates']:
        fid=c['id'];parent='KLEBORATE-UPLOAD-422' if fid=='KLEBORATE-CLIENT-COMPANION' else fid
        a=assessments['issues'][parent];issue=issues[parent];test=checks[fid]
        repo=REPO/'bonsai-sdk' if c['repository']=='SDK' else REPO
        head=subprocess.check_output(['git','-C',str(repo),'rev-parse',c['branch']],text=True).strip()
        assert head==c['head']
        patch=subprocess.check_output(['git','-C',str(repo),'diff','--binary',c['base_commit'],head])
        row={**c,'title':TITLES[fid],'review_band':a['review_band'],'normal_workflow':a['normal_workflow'],
             'minimal_fix':a['minimal_fix'],'caveat':a['caveat'],'verification':test,'merge_note':MERGE_NOTES.get(fid),
             'body':fid.lower()+'.md','patch_sha256':sha256(patch).hexdigest(),
             'resolution':'Conditional containment; privacy P0 remains open for existing private data' if fid=='PRIVATE-RECORD-SCOPE' else 'Targeted fix; stated validation limits apply'}
        row.pop('validation',None)
        if fid=='KLEBORATE-CLIENT-COMPANION':row['minimal_fix']='Add one optional input path and bind it as a multipart file; close both file handles.'
        paired=['KLEBORATE-CLIENT-COMPANION'] if fid=='KLEBORATE-UPLOAD-422' else ['KLEBORATE-UPLOAD-422'] if fid=='KLEBORATE-CLIENT-COMPANION' else []
        row['paired_candidates']=paired
        branchcmd='git -C '+shlex.quote(str(repo))+' push -u origin '+shlex.quote(c['branch'])
        row['user_publish_command']=branchcmd
        size=f"+{c['production_added']}/-{c['production_removed']} production lines in {len(c['files'])} file(s), relative to {c['base_ref']}."
        description=issue['observed']+' '+row['minimal_fix']
        if fid=='KLEBORATE-CLIENT-COMPANION':description='The SDK cannot supply the companion file accepted by the paired API change. '+row['minimal_fix']
        if fid=='PRIVATE-RECORD-SCOPE':description+=' **This rejects new private creation only. Existing private-marked records are still readable across accounts; this is not an ACL implementation or a complete P0 closure.**'
        if test['method'].startswith('Chromium'):
            command='/home/jakob/data/codex/bonsai/environments/release-test/bin/python scripts/check_minimal_pr_browser.py'
        else:command='python3 scripts/verify_minimal_prs.py --only '+fid
        dependencies=', '.join(c['dependencies']) or 'None'
        pairedtext=', '.join(paired) or 'None'
        body=f'''# {row['title']}

{description}

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
{command}
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `{c['head']}`.

### Expected outcome

{issue['acceptance'] if fid not in ['PRIVATE-RECORD-SCOPE','KLEBORATE-CLIENT-COMPANION'] else 'Public record creation remains accepted and new private-marked creation returns 422 before the service is called.' if fid=='PRIVATE-RECORD-SCOPE' else 'Both files are sent as multipart parts and both handles close after the request.'}

Recorded result: {test['passed']} focused checks passed ({test['method']}). Logs and source heads are pinned in the local verification ledger. {a['caveat']}

### Additional context

- Finding: `{fid}`; apparent priority: {issue['priority']}.
- Repository: {c['repository']}; base: `{c['base_ref']}` (`{c['base_commit']}`).
- {size}
- Git prerequisites: {dependencies}.
- Paired repository candidate: {pairedtext}.
- Normal trigger: {a['normal_workflow']}
- Selection assessment: {a['review_band']}.
- Scope limit: {row['resolution']}.
'''
        if row['merge_note']:body+='- Integration note: '+row['merge_note']+'\n'
        if fid.startswith('KLEBORATE-'):
            body+='- Operational authorization prerequisite: `pr/account-role-permissions` then `pr/analysis-upload-role-gate` for the dedicated uploader role. Live ingestion has not been performed.\n'
        body+='\nPublication is performed by the user when selected:\n\n```bash\n'+branchcmd+'\n```\n'
        (OUTPUT/row['body']).write_text(body)
        packaged.append(row)
    catalog={'created_at':datetime.now(timezone.utc).isoformat(),'application_base':manifest['application_base'],'sdk_base':manifest['sdk_base'],
             'issue_count':38,'branch_count':len(packaged),'production_only':True,'remote_publication_performed':False,
             'scope':verified['scope'],'assessment_basis':assessments['basis'],'selection_rule':assessments['selection_rule'],
             'verification':verified,'integration':{'trees':integration['trees'],'checks':[{k:v for k,v in x.items() if k!='command'} for x in integration['checks']],
                 'static_analysis':[{k:v for k,v in x.items() if k!='command'} for x in static],
                 'merge_resolutions':list(dict.fromkeys(MERGE_NOTES.values()))},'candidates':packaged}
    (OUTPUT/'catalog.json').write_text(json.dumps(catalog,indent=2)+'\n')
    lines=['# Local P0/P1 fix candidates','',
           'Actual minimal production patches are prepared in 39 local branches for 38 findings: 35 Bonsai branches and four SDK branches, including one paired upload companion. No branch or PR has been published. The development baseline catalog remains unchanged by candidate status.','',
           '**Privacy remains conditional:** the public-only creation candidate rejects new private-marked records. Existing private records are not protected; a private-data deployment still has an open P0.','',
           assessments['basis'],'',assessments['selection_rule'],'',
           f"All {len(packaged)} candidate heads passed their focused checks ({verified['checks_passed']} checks). A detached composition passed API/frontend/SDK regressions, TypeScript checking and a production webpack build. This is bounded software verification, not live ingestion or diagnostic validation.",'',
           'The reusable checks and PR bodies stay on the audit branch; each production branch contains only its scoped fix. Three branches are stacked on explicit prerequisites. Two overlapping code areas require small import/line unions when selected together; details are in the affected bodies.','',
           '| Finding | Local branch | Base | Production lines | Review assessment |',
           '| --- | --- | --- | --- | --- |']
    for c in packaged:
        lines.append(f"| [{c['id']}]({c['body']}) | `{c['branch']}` ({c['repository']}) | `{c['base_ref']}` | +{c['production_added']}/-{c['production_removed']}, {len(c['files'])} files | {c['review_band']} |")
    lines+=['','## Inspect and publish selected candidates','',
            'Inspect the exact local diff with `git diff BASE...BRANCH` in the stated repository. Review a branch in a separate worktree if desired. Keep prerequisite PRs as their own bases; after a prerequisite is merged, rebase its child onto the updated development branch. The SDK baseline is `master` at the recorded SDK commit.','',
            'The user can run the following commands for selected branches. Nothing here has been pushed:','', '```bash']
    lines += [c['user_publish_command'] for c in packaged]
    lines+=['```','','Use the corresponding Markdown body when opening each PR. No `gh pr create` or remote publishing command has been executed.','',
             '## Reproduce the checks','',
             '```bash','python3 scripts/verify_minimal_prs.py',
             '/home/jakob/data/codex/bonsai/environments/release-test/bin/python scripts/check_minimal_pr_browser.py',
             'python3 scripts/check_minimal_pr_integration.py --validate','```','',
             'The three browser-only entries in the first command are deliberately deferred to the second command. Integration worktrees and builds are on the data drive; the live source overlays and records are unchanged.','']
    (OUTPUT/'index.md').write_text('\n'.join(lines))
    print(f'{len(packaged)} local PR bodies; {verified["checks_passed"]} focused checks; all five integration checks passed')


if __name__=='__main__':main()
