"""Render the account/session iteration while preserving the earlier reports."""

from collections import Counter
from html import escape
import json

from build_species_findings import REPO, render_chart


def render(run,output,publish,figure):
    relative='account-sessions/2026-11-07/'
    root=run/relative
    if not (root/'findings.json').exists():return '', ''
    context=json.loads((root/'context.json').read_text())
    latest={}
    for line in (root/'results.jsonl').read_text().splitlines():
        r=json.loads(line);latest[(r['phase'],r['surface'],r['role'],r['case'])]=r
    cases=list(latest.values())
    counts={p:dict(Counter(r['status'] for r in cases if r['phase']==p)) for p in ['baseline','fixed']}
    (root/'results-latest.json').write_text(json.dumps({'counts':counts,'cases':cases},indent=2)+'\n')
    links={n:publish(relative+n+'.json') for n in ['context','scope','results-latest','regressions','state-verification','findings']}
    content=json.loads((REPO/'docs/local-testing/account-findings-content.json').read_text())
    findings=json.loads((root/'findings.json').read_text())
    html=['<section class="section" id="accounts"><div class="section-heading"><h2>Account isolation and permission consistency</h2></div><div class="scope">',
        '<p><strong>Six account, permission and rendering issues passed local fix retests.</strong> Shared-browser selections are separated, stale tabs/history are refreshed, disabled sessions end clearly, and generic API operations follow the documented roles. The record-private policy gap remains open.</p>',
        f'<p><a href="{links["results-latest"]}">Exact observations</a> · <a href="{links["regressions"]}">97 passing regression and scope checks</a> · <a href="{links["scope"]}">Exact scope</a> · <a href="{links["context"]}">Run context</a></p>']
    for phase,outcomes in counts.items():
        asset='assets/accounts-'+phase+'.svg';render_chart(outcomes,output/asset)
        words=', '.join(f'{n} {status.lower()}' for status,n in outcomes.items())
        html.append(f'<figure><h3>{phase.capitalize()}</h3><img src="{asset}" width="850" height="55" alt="{escape(words)}"><figcaption>{escape(words)}; denominator {sum(outcomes.values())} recorded UI/API observations. The five N/A observations map the unfinished record-private policy; no pass is claimed for them. One additional frontend denial check was added during retesting. <a href="{links["results-latest"]}">Exact data</a>.</figcaption></figure>')
    html.append('<div class="table-wrap"><table><thead><tr><th>Permission path</th><th>Before</th><th>After</th></tr></thead><tbody>')
    for title,case,role in [('Ordinary single-record deletion','single-delete-denied','user_two'),('Uploader generic creation','record-create-role','uploader'),('Ordinary legacy list','record-legacy-list','user_one'),('Uninvited private group','private-group-read','user_two')]:
        cells=[]
        for phase in ['baseline','fixed']:
            row=next(r for r in cases if r['phase']==phase and r['surface']=='api' and r['case']==case and r['role']==role)
            status=row['observed'].get('http_status',row['observed'].get('delete_status'))
            cells.append(f'<td>HTTP {status}</td>')
        html.append('<tr><td>'+escape(title)+'</td>'+''.join(cells)+'</tr>')
    html.append('</tbody></table></div>')
    html.append('<p>Private-group owner, invitee, administrator and uninvited access behaved consistently in the UI and API. Record-level private visibility remains unenforced on the observed read/list/metadata paths. Its export request reached an unavailable-result response; no private-result export was produced from the generic fixture.</p>')
    html.append(f'<details class="technical"><summary>Accounts, preservation checks and limits</summary><div class="details-body"><p>Checks used the original four test accounts and two disposable accounts, with two separate browser profiles and shared-profile tabs. All disposable accounts, groups and records were removed. The original 125 records, 459 analysis documents, eight curation records, 12 groups and four accounts have unchanged hashes. <a href="{links["state-verification"]}">State verification</a>.</p><p>Existing unattributed browser-wide basket entries are discarded because their owning account is unknown. New selections persist per account. Two earlier basket follow-ups are now closed: account sharing and a literal undefined assay label.</p><p>Application patch: <code>{escape(context["application_patch_commit"])}</code>. TypeScript and the production build passed. Existing vendor-bundle size warnings remain. Branch source and compiled assets were tested through the local overlays; production container images were not rebuilt.</p><p>No analysis execution or curation writes were performed. Workers were stopped for the pass and restored afterward. Record deletion queued ordinary index cleanup. Existing analysis-route access restrictions were retained explicitly during the shared authentication correction. No new platform safety notice was observed.</p></div></details></div>')
    for finding in findings:
        text=content[finding['id']];badge='blocker' if text['severity']=='Proposed blocker' else 'followup'
        html.append(f'<article class="finding" id="{finding["id"]}"><div class="finding-head"><span class="badge {badge}">{escape(text["severity"])} · {escape(finding["status"])}</span><h3>{escape(text["title"])}</h3></div><div class="finding-body"><p>{escape(text["impact"])}</p><p class="retest"><strong>Fix verification</strong>{escape(finding["summary"])}</p>')
        if finding['screenshots']:
            html.append('<div class="gallery">');html.extend(figure(s) for s in finding['screenshots']);html.append('</div>')
        html.append(f'<p class="retest"><strong>Retest</strong>{escape(text["retest"])}</p></div></article>')
    html.append('</section>')
    return ''.join(html),'The account/session iteration verified six fixes, with 97 passing regression and scope checks. The record-private access policy gap remains open. Earlier test phases and remaining smaller findings are preserved below.'
