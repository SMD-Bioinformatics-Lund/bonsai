"""Render frozen-input parser fidelity and read-only display evidence."""

from collections import Counter
from html import escape
import json

from build_species_findings import REPO,render_chart


def render(run,output,publish,figure):
    relative='parser-display/2026-11-07/';root=run/relative
    if not (root/'findings.json').exists():return '', ''
    context=json.loads((root/'context.json').read_text());coverage=json.loads((root/'coverage.json').read_text())
    content=json.loads((REPO/'docs/local-testing/parser-findings-content.json').read_text())
    findings=json.loads((root/'findings.json').read_text());contracts=json.loads((root/'parser-contract-results.json').read_text())
    latest={}
    for line in (root/'results.jsonl').read_text().splitlines():
        row=json.loads(line);latest[(row['phase'],row['surface'],row['case'],row['sample'],row['software'],row['role'])]=row
    cases=list(latest.values());counts={phase:dict(Counter(row['status'] for row in cases if row['phase']==phase)) for phase in ['baseline','fixed']}
    (root/'results-latest.json').write_text(json.dumps({'counts':counts,'cases':cases,'interpretation':'Latest valid observation per phase, surface, case, sample, software and role. N/A is a recorded integration/configuration gap, not a pass.'},indent=2)+'\n')
    links={name:publish(relative+name+'.json') for name in ['context','scope','coverage','parser-contract-results','results-latest','regressions','state-verification','findings']}
    summary='All 479 frozen reports and 2,029 selected source fields pass offline parser checks. Seven parser/display defects were fixed and retested. Kleborate ingestion and SPA/SCCmec display coverage remain open.'
    html=['<section class="section" id="parsers"><div class="section-heading"><h2>Do parsed report values reach the interface correctly?</h2></div><div class="scope">',
          '<p><strong>The selected frozen input values are preserved through the available paths.</strong> All 479 report parses and 2,029 selected literal fields pass offline checks. All 1,969 selected fields with stored counterparts match the API; the remaining 60 belong to the un-ingested Kleborate fixtures. All 80 existing sample summaries retain their identities. Seven parser/display defects found by the additional tests were fixed locally.</p>',
          f'<p><a href="{links["coverage"]}">Exact coverage matrix</a> · <a href="{links["parser-contract-results"]}">Offline contract observations</a> · <a href="{links["results-latest"]}">API/browser observations</a> · <a href="{links["regressions"]}">314 passing regression and scope tests</a></p>']
    # Software-key coverage is distinct from producer-version validation.
    parts=[(14,'#387556'),(3,'#c89d2f'),(5,'#778994')];x=0;rectangles=[]
    for count,color in parts:
        width=850*count/22;rectangles.append(f'<rect x="{x:.2f}" y="8" width="{width:.2f}" height="32" fill="{color}"/>');x+=width
    asset='assets/parser-coverage.svg';(output/asset).write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 850 55" role="img"><title>22 registered parser keys: 14 with frozen application fixtures, 3 additional generic QC examples, 5 without application fixtures</title>'+''.join(rectangles)+'</svg>')
    html.append(f'<figure><img src="{asset}" width="850" height="55" alt="14 frozen application formats, 3 additional generic QC formats, 5 without application fixtures"><figcaption>Coverage of 22 registered parser keys: green = 14 with frozen application fixtures; amber = three additional generic QC examples; grey = five without application fixtures. The 196 passing SDK tests also use pinned upstream library fixtures. Registry ranges and dispatch checks do not validate every producer version. <a href="{links["coverage"]}">Exact data</a>.</figcaption></figure>')
    html.append('<div class="table-wrap"><table><thead><tr><th>Observed behavior</th><th>Before</th><th>After</th></tr></thead><tbody>')
    for title,before,after in [
        ('Selected Mykrobe result','UnboundLocalError','Selected value retained'),
        ('Header-only Bracken report','Parsed; nested dictionary','Empty; []'),
        ('Two coverage rows from a stream','1 row retained','2 rows retained'),
        ('EMM summary reading surface','0 / 20','20 / 20, including empty reports'),
        ('Positive EMM table projections','18 values omitted','18 values retained'),
        ('Existing extended summary','HTTP 500','HTTP 200'),
        ('Short database-version link','Full version only in URL','Full title and accessible label')]:
        html.append('<tr>'+''.join('<td>'+escape(cell)+'</td>' for cell in [title,before,after])+'</tr>')
    html.append('</tbody></table></div><p>CSV/TSV checks matched literal species, MLST and EMM values and the record identity in 20 exported files. Another 20 requests had no file because the configured export requires a missing MLST report. The existing default overview layout does not request EMM columns; no group layout or record was changed.</p>')
    html.append('<div class="table-wrap"><table><thead><tr><th>Existing assay path</th><th>Frozen report parses</th><th>Summary identities</th><th>Integration note</th></tr></thead><tbody>')
    for row in coverage['assays']:
        note='Kleborate not stored' if row['stored_kleborate']=='missing' else 'SPA/SCCmec UI unresolved' if row['assay'] in ['saureus','staphylococcus'] else 'Selected fields matched'
        html.append(f'<tr><td>{escape(row["assay"])}</td><td>{row["offline_report_passes"]}/{row["offline_reports"]}</td><td>{row["browser_identity_passes"]}/{row["records"]}</td><td>{note}</td></tr>')
    html.append('</tbody></table></div>')
    html.append(f'<details class="technical"><summary>Exact observations and parser/version matrix</summary><div class="details-body"><p>The corrected expanded offline baseline contains 710 passes and four failures. After the SDK patch all 714 contract observations pass. These include 479 valid report executions, 80 per-record field comparisons covering 2,029 fields, 48 dispatch-boundary checks, 44 version rejections, 31 selected-result checks, 17 generic-format cases, 14 path/stream comparisons and one two-row stream check. <a href="{links["parser-contract-results"]}">Exact contract observations</a>.</p>')
    for phase,outcomes in counts.items():
        chart='assets/parser-display-'+phase+'.svg';render_chart(outcomes,output/chart)
        words=', '.join(f'{n} {status.lower()}' for status,n in outcomes.items())
        html.append(f'<figure><h3>{phase.capitalize()} API/browser observations</h3><img src="{chart}" width="850" height="55" alt="{escape(words)}"><figcaption>{escape(words)}; denominator {sum(outcomes.values())} observations. Additional percentage, projection and export checks were added during the pass, so phase totals differ. N/A maps missing counterparts, unsupported displays or an unchanged layout. These counts are not product coverage percentages. <a href="{links["results-latest"]}">Exact data</a>.</figcaption></figure>')
    html.append('<div class="table-wrap"><table><thead><tr><th>Registered parser key</th><th>Frozen input versions / reports</th><th>Additional generic QC example</th></tr></thead><tbody>')
    for item in coverage['parsers']:
        versions=', '.join(f'{v} / {n}' for v,n in item['fixture_versions'].items()) or 'No application fixture'
        html.append(f'<tr><td>{escape(item["parser"])}</td><td>{escape(versions)}</td><td>{"Tested" if item.get("generic_qc_contract_example") else "—"}</td></tr>')
    html.append('</tbody></table></div></div></details>')
    html.append(f'<details class="technical"><summary>Method, reproducibility and limits</summary><div class="details-body"><p>Expected literal values come from the frozen inputs or their separately recorded fixture expectations. API values are not used as parser expectations. Browser checks cover record identity, numeric QC, percentage formatting, MLST, EMM, extended species rows and stored provenance. No curation, viewer or analysis actions were submitted. Automatic similarity requests were blocked; related background-error toasts can appear in screenshots.</p><p>All original 125 records, 459 analysis documents, eight curation records, 12 groups and four accounts have unchanged canonical hashes. No new database records were created. <a href="{links["state-verification"]}">Preservation verification</a>. Workers were stopped during testing and restored afterward. No new platform safety notice was observed.</p><p>Application patch: <code>{context["application_patch_commit"]}</code> on <code>fix/critical-ui-release-pass</code>. SDK patch: <code>{context["sdk_patch_commit"]}</code> on the independently committed nested <code>bonsai-sdk</code> branch <code>fix/parser-display-fidelity</code>. Both source overlays are active locally. Start them with <code>bash scripts/parser-display-test.sh up</code>; <code>restore-image-sdk</code> restores the image-provided SDK while retaining the application overlay. Images were not rebuilt; JavaScript was unchanged.</p><p>Running parser modules on fixed reports does not run JASEN or sequence analysis. The SDK suite uses its pinned upstream test fixtures; the application/browser comparison uses the original synthetic fixture set. Generic additional QC cases are examples of the installed parser contract and do not establish actual producer-version compatibility.</p><p>Real JASEN outputs, additional supported-format versions, production-size reports and scientific correctness remain unvalidated. Kleborate needs a separately scoped ingestion test. SPA/SCCmec reading surfaces and overview configuration still require product decisions. The earlier record-private policy gap and recovery follow-ups remain open. <a href="{links["context"]}">Context, source revisions and harness corrections</a>.</p></div></details></div>')
    for finding in findings:
        text=content[finding['id']];badge='blocker' if text['severity']=='Proposed blocker' else 'followup'
        html.append(f'<article class="finding" id="{finding["id"]}"><div class="finding-head"><span class="badge {badge}">{escape(text["severity"])} · {escape(finding["status"])}</span><h3>{escape(text["title"])}</h3></div><div class="finding-body"><p>{escape(text["impact"])}</p><p class="retest"><strong>Verification</strong>{escape(text["summary"])}</p>')
        if text['screenshots']:
            html.append('<div class="gallery">');html.extend(figure(shot) for shot in text['screenshots']);html.append('</div>')
        html.append('</div></article>')
    html.append('</section>')
    return ''.join(html),summary
