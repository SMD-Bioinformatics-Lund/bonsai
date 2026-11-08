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
    tb_fixture=HUB/'cases/mtuberculosis/saved-qc-software-test'
    tb_verification=json.loads((tb_fixture/'verification-status.json').read_text()) if (tb_fixture/'verification-status.json').exists() else {}
    kleb_file=HUB/'cases/klebsiella/fixture-preflight.json'
    kleb_preflight=json.loads(kleb_file.read_text()) if kleb_file.exists() else {}
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
        reason=('Saved numeric-QC case imported; missing-analysis wording reproduced; biological reports excluded' if key=='mtuberculosis' else
            'Saved-report software case imported; SPA display and missing-analysis wording findings' if key=='saureus' else
            'Completed public producer result imported and browser-checked') if stored else (
            'Input preparation interrupted after the reported biological content restriction; no producer run or import started'
            if key=='saureus' else 'Earlier synthetic coverage confirmed for both aliases; duplicate QC import skipped because fixture provenance is inconsistent'
            if key=='klebsiella' and kleb_preflight else 'No new producer result loaded; sequence-processing expansion stopped')
        profiles.append({'key':key,'label':definition['label'],'records':stored,'record_count':len(stored),'status':reason})
    document={'observed_at_utc':now(),'instance':frontend,'scope':'Existing public-data pilot plus explicitly labelled saved-report software fixtures, viewed as pilot_viewer; earlier synthetic test instances are excluded',
        'new_sequence_analyses_started':0,'native_expansion_status':'Stopped after a user-supplied biological content restriction',
        'trigger_identified':False,'profiles':profiles,'saved_report_verification':verification,'tb_saved_qc_verification':tb_verification,
        'klebsiella_fixture_preflight':kleb_preflight,
        'coverage_note':'Loaded-profile counts describe this newer instance only; earlier synthetic parser and browser identity checks covered every configured profile'}
    public=HUB/'docs';(public/'data').mkdir(parents=True,exist_ok=True)
    write(public/'data/loaded-results.json',document)
    if verification:
        write(public/'data/saureus-software-checks.json',verification)
        shutil.copy2(Path(__file__).resolve().parents[2]/'datasets/bonsai_saved_report_case.json',public/'data/saved-report-provenance.json')
    if tb_verification:
        write(public/'data/tb-software-checks.json',tb_verification)
        shutil.copy2(Path(__file__).resolve().parents[2]/'datasets/bonsai_tb_saved_qc_case.json',public/'data/tb-qc-provenance.json')
    if kleb_preflight:
        write(public/'data/klebsiella-fixture-preflight.json',kleb_preflight)
    loaded=sum(p['record_count']>0 for p in profiles);total=len(profiles)
    native=sum(any(r['coverage_mode']=='native_producer' for r in p['records']) for p in profiles)
    saved=loaded-native
    checks=verification.get('checks',[]);passed=sum(c['status']=='PASS' for c in checks);failed=len(checks)-passed
    tb_checks=tb_verification.get('checks',[]);tb_passed=sum(c['status']=='PASS' for c in tb_checks);tb_failed=len(tb_checks)-tb_passed
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 275" role="img" aria-label="{loaded} of {total} profiles have test records; S. aureus {passed} of {len(checks)}, TB QC {tb_passed} of {len(tb_checks)} checks passed"><rect width="480" height="275" fill="white"/><g font-family="sans-serif" fill="#172b3d"><text y="22" font-size="18">{loaded} of {total} profiles have test records loaded</text><rect y="40" width="480" height="25" rx="4" fill="#e4e8ed"/><rect y="40" width="{480*native/total:.2f}" height="25" fill="#16836d"/><rect x="{480*native/total:.2f}" y="40" width="{480*saved/total:.2f}" height="25" fill="#367ac0"/><text y="88" font-size="13">{native} native producer · {saved} saved-report cases · {total-loaded} not loaded</text><text y="119" font-size="17">S. aureus reports: {passed} / {len(checks)} checks passed</text><rect y="135" width="480" height="22" fill="#b84735"/><rect y="135" width="{480*passed/max(1,len(checks)):.2f}" height="22" fill="#16836d"/><text y="181" font-size="13">{passed} passed · {failed} failed · one saved fixture bundle</text><text y="209" font-size="17">TB numeric QC: {tb_passed} / {len(tb_checks)} checks passed</text><rect y="224" width="480" height="22" fill="#b84735"/><rect y="224" width="{480*tb_passed/max(1,len(tb_checks)):.2f}" height="22" fill="#16836d"/><text y="269" font-size="13">{tb_passed} passed · {tb_failed} failed · one saved QC fixture bundle</text></g></svg>'''
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
    findings=f'<section><h2>S. aureus saved-report software check</h2><p>{passed} of {len(checks)} checks passed. All four report-to-store comparisons passed; ordinary search, identity, QC display, provenance metadata and CSV export passed. SPA display and omitted-analysis wording failed. The automatic widget also logged an error for this unindexed case.</p><div class="table"><table><thead><tr><th>Priority</th><th>Finding</th><th>Evidence</th><th>When triggered</th><th>Expected fix scope</th></tr></thead><tbody>{finding_rows}</tbody></table></div><p>Priorities reflect apparent user impact; workflow frequency is not measured. The SPA surface gap was already P2 in the development report. No production fixes were applied in this increment. <a href="data/saureus-software-checks.json">Exact checks and console observation</a> · <a href="data/saved-report-provenance.json">Pinned source files and hashes</a>.</p><p>This case contains saved spaTyper, Quast and Samtools coverage/stats reports; bedcov is an auxiliary input. The reports are mixed repository fixtures, not one coherent newly analysed isolate. Resistance/virulence reports, raw reads, schemas, variants, references and indexes were omitted. This verifies software behavior and does not establish a species-based permission boundary.</p></section>' if verification else ''
    tb_finding_rows=''.join(f'<tr><td><strong>{e(f["priority"])}</strong></td><th>{e(f["title"])}</th><td>{e(f["observed"])}</td><td>{e(f["trigger_likelihood"])}</td><td>{e(f["fix_size"])}</td></tr>' for f in sorted(tb_verification.get('findings',[]),key=lambda f:f['priority']))
    tb_findings=f'<section id="tb-qc"><h2>TB profile: saved numeric-QC check</h2><p><strong>{tb_passed} of {len(tb_checks)} checks passed.</strong> Two QC reports were imported: Quast and legacy PostAlignQC. All nine assembly metrics, twelve alignment-QC scalar metrics and seven coverage bins were preserved. Tables and the plotted bin values matched the stored data. Search, identity, metadata, CSV export, the empty-detail availability message and read-only persistence passed.</p><p>The P1 omitted-analysis negative wording and P2 unindexed-widget error from the S. aureus case were reproduced. No additional distinct issue was found. These observations concern data availability and UI behavior, not biological predictions.</p><div class="table"><table><thead><tr><th>Priority</th><th>Finding</th><th>Evidence</th><th>When triggered</th><th>Expected fix scope</th></tr></thead><tbody>{tb_finding_rows}</tbody></table></div><p>Only existing numeric-QC fixtures were used. No native producer run, raw sequences, typing schemas, resistance/virulence/lineage reports, variant files, references or indexes were included. Fixture values were checked literally; their original semantics and sample coherence were not independently validated. The legacy producer version is unknown, so <code>0.0.0+fixture.unknown</code> is an explicit synthetic metadata placeholder.</p><p><a href="data/tb-software-checks.json">Exact TB checks and console observations</a> · <a href="data/tb-qc-provenance.json">Pinned QC sources and hashes</a>. No production code was changed.</p></section>' if tb_verification else ''
    kleb_findings='<section id="klebsiella-preflight"><h2>Klebsiella: prior coverage confirmed; duplicate QC import skipped</h2><p><strong>Earlier synthetic tests already covered both <code>kpneumoniae</code> and <code>klebsiella</code>.</strong> Offline parsing and browser identity checks passed. Another QC-only import would largely repeat those checks, so no additional record was imported into this newer instance.</p><p><strong>P2 fixture-provenance issue:</strong> the pinned repository fixture declares <code>ecoli</code> in its run metadata. Its Quast assembly label is <code>ecoli_test_1</code>, and that report is byte-identical to the E. coli fixture. It remains useful for generic parser checks; it cannot establish representative Klebsiella producer coverage.</p><p>This is triggered when the fixture is treated as a representative Klebsiella result. A small fixture metadata correction and an accurately labelled or replaced QC report would address that limitation; no production refactoring is indicated. Complete saved-report Kleborate ingestion and display with its companion file remains a separate gap. The earlier offline passes and plumbing tests do not establish that integration.</p><p><a href="data/klebsiella-fixture-preflight.json">Exact prior coverage and pinned fixture evidence</a>. No new sequence processing, biological result parsing or record import was performed in this increment.</p></section>' if kleb_preflight else ''
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
    for screenshot in tb_verification.get('screenshots',[]):
        source=tb_fixture/screenshot['path']
        if source.name not in {'summary.png','qc-values.png','unavailable-detail.png'}:continue
        destination=public/'evidence/tb'/source.name;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,destination)
        caption={'summary.png':'TB-profile QC-only fixture: the summary opens. The P1 negative wording for an omitted analysis is reproduced.',
            'qc-values.png':'TB-profile saved QC: all nine assembly metrics, twelve scalar QC metrics and seven coverage-bin values were compared with the source fixtures and stored data.',
            'unavailable-detail.png':'An explicit unavailable-result message is shown on the empty variant-detail page; no biological result was imported for this view.'}[source.name]
        figures.append(f'<figure><img src="evidence/tb/{e(source.name)}" alt="{e(caption)}"><figcaption>{e(caption)} <a href="data/tb-software-checks.json">Exact checks and screenshot hashes</a>.</figcaption></figure>')
    page=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Bonsai organism coverage — loaded results</title><style>body{{font:16px/1.55 system-ui,sans-serif;margin:0;color:#172b3d;background:#f4f7fa}}main{{max-width:1050px;margin:auto;padding:24px}}section,header{{background:white;padding:22px;margin-bottom:20px;border-radius:10px}}h1{{font-size:28px;line-height:1.2}}h2{{font-size:21px}}a{{color:#056c83}}.notice{{border-left:5px solid #c18c20;padding-left:14px}}.table{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{padding:10px;text-align:left;vertical-align:top;border-bottom:1px solid #d8e1e9}}figure{{margin:20px 0}}img{{max-width:100%;height:auto}}.coverage{{width:480px}}figcaption,small{{color:#455a6d;font-size:13px}}@media(max-width:600px){{main{{padding:10px}}section,header{{padding:16px}}th,td{{padding:7px}}}}@media print{{body{{background:white}}main{{padding:0}}section,header{{break-inside:avoid}}}}</style><main><header><p>BONSAI / ORGANISM COVERAGE</p><h1>Which organism profiles have test results loaded?</h1><p>Earlier synthetic parser and browser identity checks already covered every configured profile, including both Klebsiella assay names. The count below describes records loaded into this newer instance only.</p><p><strong>{loaded} of {total} configured JASEN profiles have test records: {native} completed native public-data control and {saved} saved-report software fixtures.</strong></p><p class="notice">Fresh sequence processing remains stopped after the reported biological-content restriction; the exact trigger was not exposed. The S. aureus and TB-profile cases cover import and display of already-produced repository reports only. Completed downloads and the earlier E. coli pilot were preserved.</p><figure><img class="coverage" src="coverage.svg" alt="{loaded} of {total} profiles loaded; {passed} of {len(checks)} saved-report checks passed"><figcaption>Upper bar: profiles with test records visible to the ordinary viewing account; denominator: seven configured JASEN 1.4.1 profiles. Green is a native producer run; blue is a saved-report fixture. Lower bars: S. aureus {passed}/{len(checks)} and TB numeric QC {tb_passed}/{len(tb_checks)} checks passed. Each denominator belongs to its own single fixture case. This measures software coverage, not clinical accuracy or an organism permission list. <a href="data/loaded-results.json">Exact data</a>.</figcaption></figure><p><a href="#klebsiella-preflight">Klebsiella coverage check</a> · <a href="#tb-qc">TB QC case</a> · <a href="{frontend}">Open the test instance</a> · <a href="../development/">Development issue report</a></p><small>Snapshot: {e(document["observed_at_utc"])}. Local application/SDK fixes are active. Earlier synthetic test instances are excluded.</small></header>{kleb_findings}{tb_findings}{findings}<section><h2>Per-profile status</h2><div class="table"><table><thead><tr><th>Profile</th><th>Records</th><th>Analyses</th><th>Status</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>{''.join(details)}<section><h2>Screenshot evidence</h2>{''.join(figures)}</section></main></html>'''
    (public/'index.html').write_text(page)
    published=DATA.parent/'bonsai/docs/development-findings/organisms'
    if published.is_symlink():assert published.resolve()==public.resolve()
    elif published.exists():raise RuntimeError('Existing reading surface would be replaced')
    else:published.symlink_to(public,target_is_directory=True)
    print(f'Summary published: {loaded}/{total} profiles, {sum(p["record_count"] for p in profiles)} records; existing Bonsai records read without modification')


if __name__=='__main__':main()
