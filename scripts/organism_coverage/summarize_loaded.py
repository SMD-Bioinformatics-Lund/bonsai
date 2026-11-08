#!/usr/bin/env python3
"""Read existing Bonsai records and render the requested loaded-results summary."""
import collections
import html
import json
from pathlib import Path
import shutil
import urllib.parse
import urllib.request
from coverage_common import DATA, HUB, PILOT, cases, now, write


def main():
    api='http://127.0.0.1:18101';frontend='http://100.90.51.21:18100'
    account=json.loads((PILOT/'bonsai/accounts.json').read_text())['pilot_viewer']
    body=urllib.parse.urlencode({'username':account['username'],'password':account['password']}).encode()
    with urllib.request.urlopen(urllib.request.Request(api+'/token',data=body),timeout=30) as response:
        token=json.load(response)['access_token']
    def get(path):
        request=urllib.request.Request(api+path,headers={'Authorization':'Bearer '+token})
        with urllib.request.urlopen(request,timeout=30) as response:return json.load(response)
    listing=get('/samples?limit=50');samples=listing['data']
    assert listing.get('recordsTotal',len(samples))==len(samples),'Summary must include all visible records'
    plan=cases();profiles=[]
    fixture=HUB/'cases/saureus/saved-report-software-test'
    verification=json.loads((fixture/'verification-status.json').read_text()) if (fixture/'verification-status.json').exists() else {}
    for key in plan['order']:
        definition=plan['cases'][key];stored=[]
        for entry in samples:
            sample=get('/samples/'+entry['sample_id'])
            if not sample.get('pipeline') or sample['pipeline'].get('assay')!=key:continue
            descriptors=[a for field in ['qc_result','typing_result','element_type_result','species_prediction'] for a in sample.get(field,[])]
            tools={}
            for a in descriptors:
                tool=tools.setdefault(a['software'],{'analysis_types':set(),'statuses':collections.Counter(),'analysis_ids':set()})
                tool['analysis_types'].add(a['analysis_type']);tool['statuses'][a['status']]+=1;tool['analysis_ids'].add(a['analysis_id'])
            stored.append({'sample_id':sample['sample_id'],'external_id':sample.get('external_sample_id'),
                'name':sample['sample_name'],'record_url':frontend+'/sample/'+sample['sample_id'],
                'origin':'Saved SDK report fixture (mixed reports; no new producer run)' if sample.get('external_sample_id','').startswith('fixture_') else 'Completed native public-data producer run',
                'coverage_mode':'saved_report_fixture' if sample.get('external_sample_id','').startswith('fixture_') else 'native_producer',
                'pipeline_name':sample['pipeline']['pipeline_info']['definition']['name'],
                'pipeline_version':sample['pipeline']['pipeline_info']['definition']['version'],
                'analyses':len({a['analysis_id'] for a in descriptors}),'view_descriptors':len(descriptors),
                'tools':{name:{'analysis_types':sorted(t['analysis_types']),'statuses':dict(t['statuses']),
                    'analysis_records':len(t['analysis_ids'])} for name,t in sorted(tools.items())},
                'reference_registered':bool(sample.get('reference_genome_id')),
                'signature_registered':bool(sample.get('genome_signature')),'ska_index_registered':bool(sample.get('ska_index'))})
        reason=('Saved-report software case imported; SPA display and missing-analysis wording findings' if key=='saureus' else
            'Completed public producer result imported and browser-checked') if stored else (
            'Input preparation interrupted after the reported biological content restriction; no producer run or import started'
            if key=='saureus' else 'No new producer result loaded; sequence-processing expansion stopped')
        profiles.append({'key':key,'label':definition['label'],'records':stored,'record_count':len(stored),'status':reason})
    document={'observed_at_utc':now(),'instance':frontend,'scope':'Existing public-data pilot plus one explicitly labelled saved-report fixture, viewed as pilot_viewer; earlier synthetic test instances are excluded',
        'new_sequence_analyses_started':0,'native_expansion_status':'Stopped after a user-supplied biological content restriction',
        'trigger_identified':False,'profiles':profiles,'saved_report_verification':verification}
    public=HUB/'docs';(public/'data').mkdir(parents=True,exist_ok=True)
    write(public/'data/loaded-results.json',document)
    if verification:
        write(public/'data/saureus-software-checks.json',verification)
        shutil.copy2(Path(__file__).resolve().parents[2]/'datasets/bonsai_saved_report_case.json',public/'data/saved-report-provenance.json')
    loaded=sum(p['record_count']>0 for p in profiles);total=len(profiles)
    native=sum(any(r['coverage_mode']=='native_producer' for r in p['records']) for p in profiles)
    saved=loaded-native
    checks=verification.get('checks',[]);passed=sum(c['status']=='PASS' for c in checks);failed=len(checks)-passed
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 195" role="img" aria-label="{loaded} of {total} profiles have test records; {passed} of {len(checks)} saved-report checks passed"><rect width="480" height="195" fill="white"/><g font-family="sans-serif" fill="#172b3d"><text y="22" font-size="18">{loaded} of {total} profiles have test records loaded</text><rect y="40" width="480" height="25" rx="4" fill="#e4e8ed"/><rect y="40" width="{480*native/total:.2f}" height="25" fill="#16836d"/><rect x="{480*native/total:.2f}" y="40" width="{480*saved/total:.2f}" height="25" fill="#367ac0"/><text y="88" font-size="13">{native} native producer · {saved} saved-report case · {total-loaded} not loaded</text><text y="119" font-size="17">Saved-report case: {passed} / {len(checks)} checks passed</text><rect y="135" width="480" height="22" fill="#b84735"/><rect y="135" width="{480*passed/max(1,len(checks)):.2f}" height="22" fill="#16836d"/><text y="181" font-size="13">{passed} passed · {failed} failed · one saved S. aureus fixture bundle</text></g></svg>'''
    (public/'coverage.svg').write_text(svg)
    e=html.escape
    rows=[];details=[]
    for p in profiles:
        count=sum(r['analyses'] for r in p['records'])
        rows.append(f'<tr><th>{e(p["label"])}</th><td>{p["record_count"]}</td><td>{count}</td><td>{e(p["status"])}</td></tr>')
        for r in p['records']:
            tools=''.join(f'<tr><th>{e(name)}</th><td>{e(", ".join(t["analysis_types"]))}</td><td>{e(", ".join(k+": "+str(v) for k,v in t["statuses"].items()))}</td></tr>' for name,t in r['tools'].items())
            details.append(f'<section><h2>{e(p["label"])} — loaded results</h2><p><a href="{e(r["record_url"])}">{e(r["name"])}</a>. {r["analyses"]} analysis records and {r["view_descriptors"]} view descriptors.</p><p><strong>{e(r["origin"])}</strong>. Pipeline metadata: {e(r["pipeline_name"])} {e(r["pipeline_version"])}.</p><div class="table"><table><thead><tr><th>Stored software result</th><th>Result types</th><th>Descriptor status</th></tr></thead><tbody>{tools}</tbody></table></div><p>Reference, signature and SKA index registered: {r["reference_registered"]}, {r["signature_registered"]}, {r["ska_index_registered"]}. These are storage-presence checks.</p></section>')
    finding_rows=''.join(f'<tr><td><strong>{e(f["priority"])}</strong></td><th>{e(f["title"])}</th><td>{e(f["observed"])}</td><td>{e(f["trigger_likelihood"])}</td><td>{e(f["fix_size"])}</td></tr>' for f in sorted(verification.get('findings',[]),key=lambda f:f['priority']))
    findings=f'<section><h2>Saved-report software check: findings</h2><p>{passed} of {len(checks)} checks passed. All four report-to-store comparisons passed; ordinary search, identity, QC display, provenance metadata and CSV export passed. SPA display and omitted-analysis wording failed. The automatic widget also logged an error for this unindexed case.</p><div class="table"><table><thead><tr><th>Priority</th><th>Finding</th><th>Evidence</th><th>When triggered</th><th>Expected fix scope</th></tr></thead><tbody>{finding_rows}</tbody></table></div><p>Priorities reflect apparent user impact; workflow frequency is not measured. The SPA surface gap was already P2 in the development report. No production fixes were applied in this increment. <a href="data/saureus-software-checks.json">Exact checks and console observation</a> · <a href="data/saved-report-provenance.json">Pinned source files and hashes</a>.</p><p>This case contains saved spaTyper, Quast and Samtools coverage/stats reports; bedcov is an auxiliary input. The reports are mixed repository fixtures, not one coherent newly analysed isolate. Resistance/virulence reports, raw reads, schemas, variants, references and indexes were omitted. This verifies software behavior and does not establish a species-based permission boundary.</p></section>' if verification else ''
    figures=[]
    fidelity=json.loads((PILOT/'bonsai/fidelity-status.json').read_text())
    for image in fidelity.get('screenshots',[]):
        source=PILOT/image['path'];destination=public/'evidence/ecoli'/source.name;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,destination)
        figures.append(f'<figure><img src="evidence/ecoli/{e(source.name)}" alt="Existing E. coli software-test screenshot"><figcaption>Existing E. coli pilot screenshot: {e(source.stem.replace("-"," "))}. The source screenshot and completed pilot were preserved.</figcaption></figure>')
    for screenshot in verification.get('screenshots',[]):
        source=fixture/screenshot['path']
        if source.name not in {'summary.png','qc-values.png','metadata.png'}:continue
        destination=public/'evidence/saureus'/source.name;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,destination)
        caption={'summary.png':'Saved S. aureus report case: the summary loads but the stored SPA result has no card. The omitted-analysis negative wording is visible above the QC section.',
            'qc-values.png':'Saved quality reports: displayed assembly metrics, read-pair count and both per-contig depths were compared with the stored data.',
            'metadata.png':'The ordinary viewing account can read the explicit fixture provenance and limited software-test scope.'}[source.name]
        figures.append(f'<figure><img src="evidence/saureus/{e(source.name)}" alt="{e(caption)}"><figcaption>{e(caption)} <a href="data/saureus-software-checks.json">Exact checks and screenshot hashes</a>.</figcaption></figure>')
    page=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Bonsai organism coverage — loaded results</title><style>body{{font:16px/1.55 system-ui,sans-serif;margin:0;color:#172b3d;background:#f4f7fa}}main{{max-width:1050px;margin:auto;padding:24px}}section,header{{background:white;padding:22px;margin-bottom:20px;border-radius:10px}}h1{{font-size:28px;line-height:1.2}}h2{{font-size:21px}}a{{color:#056c83}}.notice{{border-left:5px solid #c18c20;padding-left:14px}}.table{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{padding:10px;text-align:left;vertical-align:top;border-bottom:1px solid #d8e1e9}}figure{{margin:20px 0}}img{{max-width:100%;height:auto}}.coverage{{width:480px}}figcaption,small{{color:#455a6d;font-size:13px}}@media(max-width:600px){{main{{padding:10px}}section,header{{padding:16px}}th,td{{padding:7px}}}}@media print{{body{{background:white}}main{{padding:0}}section,header{{break-inside:avoid}}}}</style><main><header><p>BONSAI / ORGANISM COVERAGE</p><h1>Which organism profiles have test results loaded?</h1><p><strong>{loaded} of {total} configured JASEN profiles have test records: {native} completed native public-data control and {saved} saved-report software fixture.</strong></p><p class="notice">Fresh sequence processing remains stopped after the reported biological-content restriction; the exact trigger was not exposed. The additional S. aureus case covers import and display of already-produced repository reports only. Completed downloads and the earlier E. coli pilot were preserved.</p><figure><img class="coverage" src="coverage.svg" alt="{loaded} of {total} profiles loaded; {passed} of {len(checks)} saved-report checks passed"><figcaption>Upper bar: profiles with test records visible to the ordinary viewing account; denominator: seven configured JASEN 1.4.1 profiles. Green is a native producer run; blue is a saved-report fixture. Lower bar: {passed} passed and {failed} failed checks in the single saved-report case. This measures software coverage, not clinical accuracy or an organism permission list. <a href="data/loaded-results.json">Exact data</a>.</figcaption></figure><p><a href="{frontend}">Open the test instance</a> · <a href="../development/">Development issue report</a></p><small>Snapshot: {e(document["observed_at_utc"])}. Local application/SDK fixes are active. Earlier synthetic test instances are excluded.</small></header>{findings}<section><h2>Per-profile status</h2><div class="table"><table><thead><tr><th>Profile</th><th>Records</th><th>Analyses</th><th>Status</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>{''.join(details)}<section><h2>Screenshot evidence</h2>{''.join(figures)}</section></main></html>'''
    (public/'index.html').write_text(page)
    published=DATA.parent/'bonsai/docs/development-findings/organisms'
    if published.is_symlink():assert published.resolve()==public.resolve()
    elif published.exists():raise RuntimeError('Existing reading surface would be replaced')
    else:published.symlink_to(public,target_is_directory=True)
    print(f'Summary published: {loaded}/{total} profiles, {sum(p["record_count"] for p in profiles)} records; existing Bonsai records read without modification')


if __name__=='__main__':main()
