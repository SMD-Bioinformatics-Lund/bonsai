"""Add the generic failure/retry iteration to the existing standalone report."""

from collections import Counter
from html import escape
import json

from build_species_findings import REPO, render_chart


def render(run, output, publish, figure):
    relative = 'failure-recovery/2026-11-07/'
    root = run / relative
    if not (root / 'findings.json').exists():
        return '', ''
    context = json.loads((root / 'context.json').read_text())
    latest = {}
    for line in (root / 'results.jsonl').read_text().splitlines():
        row = json.loads(line)
        latest[(row['phase'], row['surface'], row['role'], row['case'])] = row
    cases = list(latest.values())
    counts = {phase: dict(Counter(row['status'] for row in cases if row['phase'] == phase)) for phase in ['baseline', 'fixed']}
    (root / 'results-latest.json').write_text(json.dumps({'counts': counts, 'cases': cases,
        'interpretation': 'Latest valid observation per phase, surface, role and case; corrected harness attempts remain in private raw history. N/A maps open behavior and is not a pass.'}, indent=2) + '\n')
    links = {name: publish(relative + name + '.json') for name in ['context', 'scope-final', 'results-latest', 'regressions', 'state-verification', 'findings']}
    regression = json.loads((root / 'regressions.json').read_text())
    content = json.loads((REPO / 'docs/local-testing/recovery-findings-content.json').read_text())
    findings = json.loads((root / 'findings.json').read_text())
    summary = (f'Six save/recovery issues passed local fix retests, with {regression["passed"]} passing automated regression and scope checks. '
               'Three recovery follow-ups and the earlier record-private policy gap remain open. The report below preserves the earlier testing and screenshots.')
    html = ['<section class="section" id="recovery"><div class="section-heading"><h2>Failure recovery and data integrity</h2></div><div class="scope">',
        '<p><strong>Six issues were fixed and retested on disposable generic records.</strong> Concurrent metadata and comment saves retain their changes, comment retries avoid duplicates, and the group editor preserves independent edits and explains incomplete saves. The earlier comment-removal error is also resolved.</p>',
        f'<p><a href="{links["results-latest"]}">Exact UI/API observations</a> · <a href="{links["regressions"]}">{regression["passed"]} passing automated checks</a> · <a href="{links["scope-final"]}">Exact scope</a> · <a href="{links["context"]}">Run context and harness corrections</a></p>']
    html.append('<div class="chart-legend"><span><i class="pass"></i>Pass</span><span><i class="fail"></i>Fail</span><span><i class="na"></i>N/A · open behavior</span></div>')
    for phase, outcomes in counts.items():
        asset = 'assets/recovery-' + phase + '.svg'
        render_chart(outcomes, output / asset)
        words = ', '.join(f'{number} {status.lower()}' for status, number in outcomes.items())
        html.append(f'<figure><h3>{phase.capitalize()}</h3><img src="{asset}" width="850" height="55" alt="{escape(words)}"><figcaption>{escape(words)}; denominator {sum(outcomes.values())} recorded UI/API observations. N/A marks an open draft, batch-retry or same-field conflict limitation. Additional control checks were added during retesting, so the phase totals differ. These are scenario observations, not product coverage percentages. <a href="{links["results-latest"]}">Exact data</a>.</figcaption></figure>')
    html.append('<div class="table-wrap"><table><thead><tr><th>Integrity check</th><th>Before</th><th>After</th></tr></thead><tbody>')
    for title, case, field, unit in [
        ('Independent metadata fields retained', 'concurrent-metadata-retention', 'retained_fields', ' / 10'),
        ('Distinct identifiers for 15 comments', 'concurrent-comment-identities', 'unique_ids', ' / 15'),
        ('Comments after the same identified retry', 'comment-retry-once', 'stored_comments', ''),
        ('Changed content under a reused request key', 'comment-key-content-conflict', 'http_status', ' HTTP status'),
    ]:
        cells = []
        for phase in ['baseline', 'fixed']:
            row = next(row for row in cases if row['phase'] == phase and row['case'] == case and row['surface'] == 'api')
            cells.append(f'<td>{row["observed"][field]}{unit}</td>')
        html.append('<tr><td>' + escape(title) + '</td>' + ''.join(cells) + '</tr>')
    html.append('</tbody></table></div><p>Still open: expired-session draft recovery, resuming a partially completed membership removal, and conflict detection when two editors change the same field. Existing historical comment-ID collisions are not repaired automatically. The separate record-private policy gap and remaining earlier UI follow-ups are preserved below.</p>')
    html.append(f'<details class="technical"><summary>Method, preservation and practical limits</summary><div class="details-body"><p>Five pairs of simultaneous metadata appends and five bursts of three comments were compared with stored state. Native browser actions covered repeated clicks, interrupted writes, lost acknowledgements, two tabs, session expiry, navigation and partial membership changes. A temporary local API gate interrupted only registered disposable targets; browser fetch faults were likewise limited to owned IDs.</p><p>All four disposable records and three groups were removed. The original 125 records, 459 analysis documents, eight curation records, 12 groups and four accounts have identical canonical hashes before and after this pass. <a href="{links["state-verification"]}">Full collection verification</a>.</p><p>Application patch: <code>{escape(context["application_patch_commit"])}</code>. TypeScript and the production JavaScript build passed. The SDK was unchanged: its existing request-header support carries comment retry identities. Tests used source and compiled-asset overlays; production images were not rebuilt.</p><p>Workers were stopped during fault injection and restored afterward. The temporary API proxy was removed and closed. No analysis execution or curation writes were performed. Automatic similarity requests from sample pages were blocked by the test scope; a related background error toast can appear in screenshots. No new platform safety notice was observed.</p><p>Only this Chromium engine and this local synthetic instance were exercised. Whole-API outages, process crashes, production-scale load, real JASEN data and scientific correctness remain untested. Successful generic tests do not authorize broader biological work.</p><p>Harness corrections are recorded in the run context. They include missing metadata categories, browser navigation waits, additive row selection and repeated fault-wrapper installation. A confirmed automatic retry is counted as recovery; submitting another new form is a new intent.</p><p>Sources: <code>scripts/check_recovery.py</code>, <code>scripts/check_recovery_browser.py</code>, <code>scripts/recovery_proxy.py</code> and the scoped regression files. The archived report before this iteration is preserved on the external data drive.</p></div></details></div>')
    for finding in findings:
        text = content[finding['id']]
        badge = 'blocker' if text['severity'] == 'Proposed blocker' else 'followup'
        html.append(f'<article class="finding" id="{finding["id"]}"><div class="finding-head"><span class="badge {badge}">{escape(text["severity"])} · {escape(finding["status"])}</span><h3>{escape(text["title"])}</h3></div><div class="finding-body"><p>{escape(text["impact"])}</p><p class="retest"><strong>Verification</strong>{escape(finding["summary"])}</p>')
        if finding['screenshots']:
            html.append('<div class="gallery">')
            html.extend(figure(item) for item in finding['screenshots'])
            html.append('</div>')
        html.append(f'<p class="retest"><strong>Retest</strong>{escape(text["retest"])}</p></div></article>')
    html.append('</section>')
    return ''.join(html), summary
