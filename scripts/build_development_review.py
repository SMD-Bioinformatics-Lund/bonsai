#!/usr/bin/env python3
"""Render the pinned development issue catalog, independent of local fix status."""

import argparse
from collections import Counter
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess

from reportlab.graphics import renderSVG
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import BaseDocTemplate, Frame, Image, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle

from build_release_review import DATA, REPO, CSS, INK, MUTED, TEAL, LINE, PRIORITY_COLORS, TOKEN, digest, read, setup_styles, write_json

CONTENT = REPO / "docs/local-testing/development-review-content.json"
ASSESSMENTS = REPO / "docs/local-testing/fix-assessments.json"
PR_CATALOG = REPO / "docs/local-testing/minimal-prs/catalog.json"
AUDIT = "development-review/2026-11-08"
BASE_URL = "http://192.168.1.156:8001/development/"
EXCLUDED = {"DETAIL-COMMENT-CONTEXT-500", "MINHASH-CLUSTER-FAIL"}


def git_blob(repo, revision, path):
    return subprocess.check_output(["git", "-C", str(repo), "show", f"{revision}:{path}"])


def assemble(run, content):
    old = read(DATA / "docs/development-findings/review/data/findings-ledger.json")
    originals = {item["id"]: item for item in old["findings"]}
    expected = set(originals) - EXCLUDED
    if expected != {item["id"] for item in content["issues"]}:
        raise ValueError("Every baseline candidate needs an explicit authored decision")
    sidebar = git_blob(REPO, content['development_commit'], 'frontend/bonsai_app/blueprints/sample/templates/sidebar.html').decode()
    comment_macro = sidebar.split('{% macro comment_area(sample) %}', 1)[1].split('{% endmacro %}', 1)[0]
    if 'current_user' in comment_macro:
        raise ValueError('Reassess exclusion of the local sidebar regression')
    alias = {v: k for k, values in old["aliases"].items() for v in values}
    direct = {alias.get(item["id"], item["id"]) for file in ["findings.json", "expanded-findings.json"] for item in read(run / file)} - EXCLUDED
    sdk_cases = {"PARSER-MYKROBE-SELECTION", "PARSER-BRACKEN-EMPTY", "PARSER-COVERAGE-STREAM"}
    isolated = {item["id"] for item in read(run / AUDIT / "isolated-baseline-final.json")["cases"] if item["issue_reproduced"]}
    permission = read(run / AUDIT / "permission-gate-baseline.json")["cases"]
    if [(x["role"], x["observed_http_status"], x["stub_service_calls"]) for x in permission] != [("user", 201, 1), ("uploader", 401, 0), ("admin", 201, 1)]:
        raise ValueError("The baseline role-boundary evidence changed")
    isolated.add("ANALYSIS-UPLOAD-ROLE-GATE")
    items, audit = [], []
    for authored in content["issues"]:
        item = dict(authored)
        oid = item["id"]
        item["source_ids"] = originals[oid]["source_ids"]
        documents = {row["source_document"] for row in originals[oid]["historical_observations"]} | set(originals[oid].get("evidence", []))
        if oid in isolated:
            documents.add(f'{AUDIT}/permission-gate-baseline.json' if oid == 'ANALYSIS-UPLOAD-ROLE-GATE' else f'{AUDIT}/isolated-baseline-final.json')
        if oid in sdk_cases:
            documents.add('parser-display/2026-11-07/parser-contract-results.json')
        if oid in {'CSV-FORMULA-PREFIX', 'CSV-NEWLINE-NORMALIZATION'}:
            documents.add(f'{AUDIT}/csv-dependency-attribution.json')
        item["evidence_documents"] = sorted(documents)
        if oid == "ANALYSIS-UPLOAD-ROLE-GATE":
            basis = "Isolated baseline reproduction"
        elif oid in direct and oid != 'BASKET-UNDEFINED-ASSAY':
            basis = "Original development browser/API evidence"
        elif oid in sdk_cases:
            basis = "Recorded SDK-baseline contract test"
        elif oid in isolated:
            basis = "Isolated baseline reproduction"
        else:
            basis = "Later observation, traced to baseline source"
        item["baseline_basis"] = basis
        item["source_checks"] = []
        for filename, needle in item.pop("sources"):
            sdk = filename.startswith("sdk:")
            filename = filename[4:] if sdk else filename
            repo = REPO / "bonsai-sdk" if sdk else REPO
            revision = content["sdk_commit"] if sdk else content["development_commit"]
            source = git_blob(repo, revision, filename)
            text = source.decode()
            if needle not in text:
                raise ValueError(f"Missing baseline source anchor for {oid}: {filename} / {needle}")
            lines = text.splitlines()
            line = next(n for n, value in enumerate(lines, 1) if needle in value)
            check = {"id": oid, "repository": "SDK" if sdk else "Bonsai", "revision": revision,
                     "path": filename, "sha256": __import__("hashlib").sha256(source).hexdigest(),
                     "line": line, "anchor": needle, "excerpt": "\n".join(lines[max(0, line-4):line+4])}
            item["source_checks"].append(len(audit)); audit.append(check)
        items.append(item)
    # The two newer CSV observations use unchanged export configuration and lockfile.
    lock = "frontend/package-lock.json"
    baseline_lock = git_blob(REPO, content["development_commit"], lock)
    dependency = read(run / AUDIT / 'csv-dependency-attribution.json')
    locked_version = json.loads(baseline_lock)['packages']['node_modules/datatables.net-buttons']['version']
    if baseline_lock != (REPO / lock).read_bytes() or dependency['version'] != locked_version:
        raise ValueError("Reassess CSV attribution after dependency changes")
    ledger = {"development_commit": content["development_commit"], "sdk_commit": content["sdk_commit"],
              "as_of": content["as_of"], "counting_rule": content["counting_rule"],
              "counts_by_priority": dict(Counter(i["priority"] for i in items)),
              "counts_by_basis": {basis: sum(i['baseline_basis'] == basis for i in items) for basis in [
                  'Original development browser/API evidence', 'Isolated baseline reproduction',
                  'Recorded SDK-baseline contract test', 'Later observation, traced to baseline source']},
              "issue_count": len(items), "excluded": [
                  {"id": "DETAIL-COMMENT-CONTEXT-500", "reason": "Introduced by the local role-aware sidebar change; the baseline sidebar does not read current_user there."},
                  {"id": "MINHASH-CLUSTER-FAIL", "reason": "Explained failed-QC/ineligible-input case; no valid-input defect demonstrated."}],
              "findings": items}
    return ledger, {"source_checks": audit, "csv_lockfile_unchanged": True,
                    "baseline_comment_macro_does_not_read_current_user": True,
                    "lockfile_sha256": __import__("hashlib").sha256(baseline_lock).hexdigest(),
                    "limitation": "Anchors and hashes identify the inspected baseline implementation. Source attribution supports the recorded failure mechanism; it is not a fresh end-to-end reproduction of every later observation."}


def make_chart(counts, mobile=False):
    d = Drawing(280 if mobile else 480, 280 if mobile else 165)
    d.add(String(0, 262 if mobile else 151, "Known development items by priority", fontName="ReviewBold", fontSize=12 if mobile else 10, fillColor=colors.HexColor(INK)))
    for n, priority in enumerate(["P0", "P1", "P2", "P3"]):
        y = (225 if mobile else 119) - n * (32 if mobile else 29)
        count = counts.get(priority, 0)
        width = count * (5.2 if mobile else 8)
        d.add(String(0, y + 2, priority, fontName="ReviewBold", fontSize=11 if mobile else 10, fillColor=colors.HexColor(INK)))
        d.add(Rect(31, y-1, width, 19 if mobile else 17, fillColor=colors.HexColor(PRIORITY_COLORS[priority]), strokeColor=None))
        d.add(String(38+width, y+2, str(count), fontName="ReviewBold", fontSize=11 if mobile else 10, fillColor=colors.HexColor(INK)))
    for x, y, value, label in ([(0, 47, sum(counts.values()), "known items"), (150, 47, counts["P0"]+counts["P1"], "P0 / P1")] if mobile else [(365, 101, sum(counts.values()), "known items"), (365, 45, counts["P0"]+counts["P1"], "P0 / P1")]):
        d.add(String(x, y, str(value), fontName="ReviewBold", fontSize=28, fillColor=colors.HexColor(TEAL)))
        d.add(String(x, y-18, label, fontName="Review", fontSize=10, fillColor=colors.HexColor(MUTED)))
    return d


def make_patch_chart(catalog, mobile=False):
    bins=[('1-5',1,5),('6-10',6,10),('11-25',11,25),('26-50',26,50),('51+',51,100000)]
    counts={label:sum(lo<=x['production_added']+x['production_removed']<=hi for x in catalog['candidates']) for label,lo,hi in bins}
    d=Drawing(280 if mobile else 480,158)
    unit=(190 if mobile else 370)/max(counts.values())
    for n,(label,count) in enumerate(counts.items()):
        y=130-n*28
        d.add(String(0,y+2,label,fontName='Review',fontSize=11,fillColor=colors.HexColor(INK)))
        d.add(Rect(57,y-2,count*unit,18,fillColor=colors.HexColor(TEAL),strokeColor=None))
        d.add(String(65+count*unit,y+2,str(count),fontName='ReviewBold',fontSize=11,fillColor=colors.HexColor(INK)))
    return d,counts


def patch_size(item):
    candidates=item['local_candidates']
    if not candidates:return ''
    return '; '.join(c['repository']+' +'+str(c['production_added'])+'/-'+str(c['production_removed'])+' in '+str(len(c['files']))+' file(s)' for c in candidates)+'.'


def render_pdf(output, content, ledger, drawing, images, review, patch_drawing):
    styles = setup_styles()
    styles.add(ParagraphStyle(name="Catalog", fontName="Review", fontSize=8.7, leading=11.8, textColor=colors.HexColor(INK), spaceAfter=0))
    styles.add(ParagraphStyle(name="CatalogId", fontName="ReviewBold", fontSize=7.2, leading=9.8, textColor=colors.HexColor(MUTED), spaceAfter=0))
    width = A4[0] - 88
    story = []
    def p(text, style="Body"):
        return Paragraph(text, styles[style])
    def t(text, style="Body"):
        return p(escape(text), style)
    def heading(kicker, text):
        story.extend([t(kicker.upper(), "Kicker"), t(text, "HeadingR")])
    heading("Development baseline / 8 November 2026", content["question"])
    story.extend([t(content["answer"]), p('<b>Target:</b> Bonsai <b>21eccf7</b>, with the recorded SDK <b>5789a9c</b>. Local patch status does not reduce this catalog.'), drawing])
    counts = ledger["counts_by_priority"]
    story.append(p('Figure 1. Distinct known baseline issues and scope gaps: ' + ", ".join(f'{counts[k]} {k}' for k in ['P0','P1','P2','P3']) + '. Denominator: 55 consolidated items, including 38 P0/P1 recommendations. The privacy gate is conditional; this is not a coverage percentage. '
                   '<link href="'+BASE_URL+'data/priority-counts.json" color="'+TEAL+'">Exact chart data</link> | '
                   '<link href="'+BASE_URL+'index.html" color="'+TEAL+'">HTML report</link>.', "Small"))
    story.extend([t("Where testing should start", "SubR")])
    for n, action in enumerate(content["first_actions"],1):story.append(t(f"{n}. {action}"))
    story.extend([t(content["scope"], "Small"), t("One local-only sidebar regression and the explained failed-QC clustering case are excluded. Some later discoveries are source-attributed to the baseline rather than newly replayed on a full baseline instance.", "Small"), PageBreak()])
    heading('Local review candidates / priorities unchanged', 'Which fixes are small and likely to matter?')
    story.append(t('Actual production patches are prepared in 39 local branches for 38 findings: 35 Bonsai branches and four SDK branches, including one paired upload companion. No branches or PRs have been published.'))
    story.append(t(review['assessment_basis'],'Small'))
    story.append(t(review['selection_rule'],'Small'))
    story.append(p('<b>Privacy P0 remains conditional.</b> The public-only candidate rejects new private-marked records. Existing private records remain readable across accounts; the branch is partial containment and does not implement ACLs.','Body'))
    story.append(p('<b>Verification:</b> 91 focused candidate checks passed. The composed changes passed 35 API, 24 frontend and 5 SDK regressions, TypeScript checking and a production webpack build. Generic fixtures and stubbed services were used; no live ingestion or decision writes were performed.','Small'))
    story.append(patch_drawing)
    story.append(p('Figure 2. Candidate branch sizes: added plus removed production lines, measured against each stated base. Denominator: 39 code branches, including the paired SDK upload branch. Prerequisites are additional; line count is not a complexity or risk score. <link href="'+BASE_URL+'data/patch-size-counts.json" color="'+TEAL+'">Exact data</link>.','Small'))
    story.append(p('<b>Selection:</b> start with the role boundary and small deterministic preservation/filtering fixes. Review feature-specific failures against local usage. Concurrent-save and retry candidates depend more on collaboration and network conditions. Every catalog item below includes its actual trigger and minimal scope.','Small'))
    story.append(p('<b>Review details:</b> <link href="'+BASE_URL+'prs/index.html" color="'+TEAL+'">Local PR index, diffs and user publication commands</link>. Three child branches have explicit prerequisites. Two overlapping areas need small import/line unions when combined; the affected PR bodies record them.','Small'))
    story.append(PageBreak())
    # Measure rows before pagination so the extra assessments remain legible.
    rows=[]
    for item in ledger['findings']:
        a=item['fix_assessment']
        left=[p('<font color="'+PRIORITY_COLORS[item['priority']]+'"><b>'+item['priority']+' / '+escape(item['area'])+'</b></font>','Catalog'),Spacer(1,4),t(item['title'],'Catalog'),Spacer(1,5),t(item['id'],'CatalogId')]
        detail=escape(item['observed'])+'<br/><b>Why urgent:</b> '+escape(item['why'])+'<br/><b>Normal trigger:</b> '+escape(a['normal_workflow'])+'<br/><b>Minimal fix:</b> '+escape(a['minimal_fix'])+' '+escape(patch_size(item))+'<br/><b>Review:</b> '+escape(a['review_band'])+'.'
        deps=sorted({dep for c in item['local_candidates'] for dep in c['dependencies']})
        if deps:detail+='<br/><b>Prerequisite:</b> '+escape(', '.join(deps))+'.'
        if item['id'] in {'PRIVATE-RECORD-SCOPE','KLEBORATE-UPLOAD-422','CURATION-DOUBLE-SUBMIT','RECOVERY-COMMENT-RETRY'}:detail+='<br/><b>Limit:</b> '+escape(a['caveat'])
        detail+='<br/><font size="7.1" color="'+MUTED+'">'+escape(item['baseline_basis'])+' | <link href="'+BASE_URL+'index.html#'+item['id']+'" color="'+TEAL+'">Evidence, acceptance and PR</link></font>'
        rows.append([left,p(detail,'Catalog')])
    chunks=[];chunk=[];height=0
    for row in rows:
        probe=Table([row],colWidths=[140,width-140]);probe.setStyle(TableStyle([('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9)]))
        rh=probe.wrap(width,10000)[1]
        if chunk and height+rh>640:chunks.append(chunk);chunk=[];height=0
        chunk.append(row);height+=rh
    if chunk:chunks.append(chunk)
    if len(chunks)>1 and len(chunks[-1])==1:
        while len(chunks[-1])<3 and len(chunks[-2])>3:
            chunks[-1].insert(0,chunks[-2].pop())
    for n, chunk in enumerate(chunks,1):
        heading(f"Catalog {n} of {len(chunks)}", "Known issues in development")
        story.append(t('Baseline urgency is unchanged by local patches. Workflow likelihood is an inference. Patch sizes exclude prerequisites; lower-priority scopes are estimates.','Small'))
        table=Table(chunk,colWidths=[140,width-140],hAlign="LEFT")
        table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9),('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor(LINE))]))
        story.extend([table,PageBreak()])
    heading("Original baseline screenshots", "Two visible development failures")
    for item,path in zip(content["screenshots"],images):
        iw,ih=struct.unpack('>II',path.read_bytes()[16:24]);scale=min(width/iw,220/ih)
        story.extend([t(item["title"],"SubR"),Image(str(path),iw*scale,ih*scale,hAlign="LEFT"),Spacer(1,6),t(item["caption"],"Small"),p('<link href="'+BASE_URL+'assets/'+path.name+'" color="'+TEAL+'">Original full-resolution PNG</link>',"Tiny"),Spacer(1,8)])
    story.extend([t("The screenshots are unchanged original files from the synthetic development baseline. Catalog links expose the saved observations and pinned source evidence.","Small"),PageBreak()])
    heading("Evidence and practical limits", "What supports this development catalog?")
    for basis,count in ledger["counts_by_basis"].items():story.append(p('<b>'+escape(basis)+': '+str(count)+' items.</b>',"Body"))
    story.append(t("The source-traced group was observed after some local changes, then checked against the relevant implementation at the pinned development/SDK revisions. These are not fresh end-to-end baseline reproductions. The isolated checks use generic in-memory records or a stubbed service, without the running API or database.","Small"))
    for item in content["limits"]:story.append(t(item,"Small"))
    story.extend([t("Priority definitions","SubR")])
    for priority,meaning in content["priorities"].items():story.append(p('<b>'+priority+':</b> '+escape(meaning),"Small"))
    story.append(p('<b>Detailed evidence:</b> <link href="'+BASE_URL+'index.html" color="'+TEAL+'">HTML catalog</link> | <link href="'+BASE_URL+'technical.html" color="'+TEAL+'">Methods and source attribution</link> | <link href="'+BASE_URL+'data/development-findings.json" color="'+TEAL+'">Machine-readable ledger</link>.',"Small"))
    pdf=output/'output/pdf/bonsai-development-issues.pdf';pdf.parent.mkdir(parents=True,exist_ok=True)
    def decorate(canvas,doc):
        canvas.saveState();canvas.setStrokeColor(colors.HexColor(LINE));canvas.setLineWidth(.6)
        canvas.line(44,A4[1]-33,A4[0]-44,A4[1]-33);canvas.setFont('ReviewBold',8);canvas.setFillColor(colors.HexColor(TEAL));canvas.drawString(44,A4[1]-25,'BONSAI / KNOWN DEVELOPMENT ISSUES / BASELINE 21eccf7')
        canvas.setFont('Review',8);canvas.setFillColor(colors.HexColor(MUTED));canvas.drawString(44,25,'8 November 2026 | Local fix status ignored | SDK baseline 5789a9c');canvas.drawRightString(A4[0]-44,25,str(doc.page));canvas.restoreState()
    doc=BaseDocTemplate(str(pdf),pagesize=A4,leftMargin=44,rightMargin=44,topMargin=48,bottomMargin=43,title=content['title'],author='Bonsai development test review',subject=content['question'])
    doc.addPageTemplates(PageTemplate(id='Development',frames=Frame(44,43,width,A4[1]-91,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0),onPage=decorate));doc.build(story)
    return pdf


def html_page(title,body):
    extra=' .priority-table{min-width:0}.source{white-space:pre-wrap;overflow-wrap:anywhere;font-size:.78rem;background:#f4f7f6;padding:12px}.finding:target{outline:3px solid #e1ba6c;outline-offset:8px}.catalog-count{font-size:.86rem;color:var(--muted)}.assessment{border-left:3px solid var(--teal);padding:3px 14px;margin:15px 0;background:#f4f8f7}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:.8rem} @media(max-width:650px){.chart{max-width:340px}}'
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+escape(title)+'</title><style>'+CSS+extra+'</style></head><body>'+body+'</body></html>'


def publish_prs(output, review):
    destination=output/'prs';destination.mkdir(exist_ok=True)
    rows=[]
    for c in review['candidates']:
        fid=c['id'];slug=fid.lower();repo=REPO/'bonsai-sdk' if c['repository']=='SDK' else REPO
        head=subprocess.check_output(['git','-C',str(repo),'rev-parse',c['branch']],text=True).strip()
        if head!=c['head']:raise ValueError('Rebuild PR metadata after branch changes: '+fid)
        patch=subprocess.check_output(['git','-C',str(repo),'diff','--binary',c['base_commit'],c['head']])
        if __import__('hashlib').sha256(patch).hexdigest()!=c['patch_sha256']:raise ValueError('Patch identity changed: '+fid)
        (destination/(slug+'.patch')).write_bytes(patch)
        shutil.copy2(PR_CATALOG.parent/c['body'],destination/c['body'])
        body='<header><p class="eyebrow">LOCAL PR CANDIDATE / '+escape(c['repository'])+'</p><h1>'+escape(c['title'])+'</h1><p><a href="index.html">All local candidates</a> | <a href="../index.html#'+('KLEBORATE-UPLOAD-422' if fid=='KLEBORATE-CLIENT-COMPANION' else fid)+'">Baseline finding</a></p></header><main><section><p><strong>'+escape(fid)+' / '+c['priority']+'</strong>. '+escape(c['resolution'])+'</p><p><strong>Normal trigger:</strong> '+escape(c['normal_workflow'])+'</p><p><strong>Minimal fix:</strong> '+escape(c['minimal_fix'])+'</p><p><strong>Size:</strong> +'+str(c['production_added'])+'/-'+str(c['production_removed'])+' production lines in '+str(len(c['files']))+' file(s), excluding prerequisites.</p><p><strong>Local branch:</strong> <code>'+escape(c['branch'])+'</code><br><strong>Base:</strong> <code>'+escape(c['base_ref'])+'</code><br><strong>Head:</strong> <code>'+c['head']+'</code></p><p><strong>Git prerequisites:</strong> '+escape(', '.join(c['dependencies']) or 'None')+'. <strong>Paired candidate:</strong> '+escape(', '.join(c['paired_candidates']) or 'None')+'.</p><p><strong>Checks:</strong> '+str(c['verification']['passed'])+' passed ('+escape(c['verification']['method'])+'). '+escape(c['caveat'])+'</p>'
        if c['merge_note']:body+='<p><strong>Combining selected fixes:</strong> '+escape(c['merge_note'])+'</p>'
        body+='<div class="links"><a href="'+slug+'.patch">Download exact production diff</a><a href="'+c['body']+'">PR body as Markdown</a></div><h2>Changed files</h2><ul>'+''.join('<li><code>'+escape(f['path'])+'</code> (+'+str(f['added'])+'/-'+str(f['removed'])+')</li>' for f in c['files'])+'</ul><details><summary>Complete review body and user publication command</summary><pre>'+escape((PR_CATALOG.parent/c['body']).read_text())+'</pre></details></section></main>'
        (destination/(slug+'.html')).write_text(html_page(c['title'],body))
        rows.append('<article class="finding"><span class="priority '+c['priority'].lower()+'">'+c['priority']+'</span><span class="id">'+escape(fid)+'</span><h3><a href="'+slug+'.html">'+escape(c['title'])+'</a></h3><p>'+escape(c['review_band'])+' / '+escape(c['repository'])+' / +'+str(c['production_added'])+'/-'+str(c['production_removed'])+' in '+str(len(c['files']))+' file(s).</p><p><code>'+escape(c['branch'])+'</code>; base <code>'+escape(c['base_ref'])+'</code>.</p></article>')
    intro='<header><p class="eyebrow">LOCAL REVIEW / NOTHING PUSHED</p><h1>Minimal P0/P1 fix candidates</h1><p class="lead">39 actual local code branches address 38 findings. Each has an exact diff, review body, verification record and a user-run publication command.</p><p><a href="../index.html#fixes">Return to development report</a> | <a href="../data/local-pr-catalog.json">Machine-readable catalog</a></p></header><main><section><p><strong>Privacy caveat:</strong> new private-marked creation is rejected, but existing private records remain exposed. This candidate does not fully close that conditional P0.</p><p>'+escape(review['assessment_basis'])+'</p><p>'+escape(review['selection_rule'])+'</p><p>Three branches depend on another local branch. The Kleborate transport change has an app/SDK pair. Two overlapping code areas need small unions when selected together; their PR bodies document the resolution.</p><p>The focused audit harness is maintained on the audit branch; production candidates contain only the scoped code fix. All 91 focused checks and all five combined checks passed. Live ingestion and decision writes remain outside this verification. The full CI service/Python-version matrix was not rerun.</p>'+''.join(rows)+'</section></main>'
    (destination/'index.html').write_text(html_page('Bonsai local P0/P1 PR candidates',intro))


def build(run,output):
    run,output=run.resolve(),output.resolve()
    if not output.is_relative_to(DATA.resolve()) or output.is_relative_to(run) or run.is_relative_to(output):raise ValueError('Generated output must be a separate directory on the external data drive')
    output.mkdir(parents=True,exist_ok=True);(output/'assets').mkdir(exist_ok=True)
    content=read(CONTENT);ledger,source_audit=assemble(run,content)
    assessments=read(ASSESSMENTS);review=read(PR_CATALOG)
    if {x['id'] for x in ledger['findings']}!=set(assessments['issues']):raise ValueError('Every finding needs a workflow and scope assessment')
    if len(review['candidates'])!=39 or review['verification']['passing']!=39:raise ValueError('Complete local candidate verification is required')
    for item in ledger['findings']:
        item['fix_assessment']=assessments['issues'][item['id']]
        item['local_candidates']=[c for c in review['candidates'] if c['id']==item['id'] or item['id']=='KLEBORATE-UPLOAD-422' and c['id']=='KLEBORATE-CLIENT-COMPANION']
    write_json(run/AUDIT/'baseline-source-audit.json',source_audit)
    write_json(output/'data/development-findings.json',ledger);write_json(output/'data/baseline-source-audit.json',source_audit)
    write_json(output/'data/priority-counts.json',{'unit':'consolidated baseline item','denominator':ledger['issue_count'],'counts':ledger['counts_by_priority'],'limits':content['counting_rule']})
    write_json(output/'data/fix-assessments.json',assessments);write_json(output/'data/local-pr-catalog.json',review)
    write_json(output/'data/candidate-verification.json',review['verification'])
    publish_prs(output,review)
    evidence={}
    evidence_files={path for item in ledger['findings'] for path in item['evidence_documents']}
    evidence_files.update([f'{AUDIT}/context.json',f'{AUDIT}/isolated-baseline-final.json',f'{AUDIT}/permission-gate-baseline.json'])
    for relative in sorted(evidence_files):
        source=(run/relative).resolve()
        if not source.is_relative_to(run) or source.suffix!='.json' or TOKEN.search(source.read_bytes()):raise ValueError('Evidence publication refused: '+relative)
        target=output/'evidence'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        evidence[relative]={'sha256':digest(source),'bytes':source.stat().st_size}
    setup_styles();drawing=make_chart(ledger['counts_by_priority'])
    for filename,figure in [('priorities.svg',drawing),('priorities-mobile.svg',make_chart(ledger['counts_by_priority'],True))]:
        target=output/'assets'/filename;renderSVG.drawToFile(figure,str(target));svg=re.sub(r'<!DOCTYPE.*?>','',target.read_text(),flags=re.S)
        svg=svg.replace('font-family: ReviewBold;','font-family: sans-serif; font-weight: 700;').replace('font-family: Review;','font-family: sans-serif;').replace('<title>...</title>','<title>Known development issues by priority</title>').replace('<desc>...</desc>','<desc>55 baseline items: P0 three, P1 thirty-five, P2 fourteen, P3 three. Local fix status is ignored.</desc>');target.write_text(svg)
    patch_drawing,patch_counts=make_patch_chart(review)
    write_json(output/'data/patch-size-counts.json',{'unit':'added plus removed production lines per candidate','denominator':39,'bins':patch_counts,'base_rule':'Each branch is measured against its stated base; prerequisite changes are additional. One paired SDK branch is included.'})
    for filename,figure in [('patch-sizes.svg',patch_drawing),('patch-sizes-mobile.svg',make_patch_chart(review,True)[0])]:
        target=output/'assets'/filename;renderSVG.drawToFile(figure,str(target));svg=re.sub(r'<!DOCTYPE.*?>','',target.read_text(),flags=re.S)
        svg=svg.replace('font-family: ReviewBold;','font-family: sans-serif; font-weight: 700;').replace('font-family: Review;','font-family: sans-serif;').replace('<title>...</title>','<title>Local candidate production patch sizes</title>').replace('<desc>...</desc>','<desc>Added plus removed production lines, grouped into five size bins for 39 local branches.</desc>');target.write_text(svg)
    images=[]
    for item in content['screenshots']:
        source=(run/item['path']).resolve()
        if not source.is_relative_to(run) or source.suffix!='.png' or source.read_bytes()[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('Only original PNG screenshots may be copied')
        target=output/'assets'/source.name;shutil.copy2(source,target);images.append(target);evidence[item['path']]={'sha256':digest(source),'bytes':source.stat().st_size}
    pdf=render_pdf(output,content,ledger,drawing,images,review,patch_drawing)
    esc=escape;counts=ledger['counts_by_priority']
    header='<header><p class="eyebrow">BONSAI / DEVELOPMENT BASELINE / 8 NOVEMBER 2026</p><h1>'+esc(content['question'])+'</h1><p class="lead">'+esc(content['answer'])+'</p><p><strong>Target: development <code>21eccf7</code> and recorded SDK <code>5789a9c</code>.</strong> The local patched candidate has a <a href="../review/index.html">separate report</a>.</p><div class="actions"><a class="primary" href="output/pdf/bonsai-development-issues.pdf">Download the PDF</a><a href="#fixes">Fix scope and likelihood</a><a href="prs/index.html">Local PRs</a><a href="technical.html">Methods and attribution</a><a href="../index.html">Detailed test history</a></div><nav aria-label="Report sections"><a href="#answer">Summary</a><a href="#fixes">Fix assessments</a>'+''.join('<a href="#'+p.lower()+'">'+p+' / '+str(counts[p])+'</a>' for p in ['P0','P1','P2','P3'])+'<a href="#screenshots">Screenshots</a><a href="#limits">Coverage and limits</a></nav></header>'
    body='<main><section id="answer"><h2>55 known baseline issues and scope gaps</h2><p>All items are assessed as development issues, whether or not a local patch was later prepared. Thirty-eight carry P0/P1 recommendations; one of the P0 gates depends on a private-record promise.</p><figure><picture><source media="(max-width:650px)" srcset="assets/priorities-mobile.svg" width="280" height="280"><img class="chart" src="assets/priorities.svg" width="480" height="165" alt="55 known baseline items: 3 P0, 35 P1, 14 P2 and 3 P3"></picture><figcaption>Figure 1. Distinct consolidated baseline items, denominator 55. Comparison: recommended urgency categories, with local patch status ignored. Product-scope and export-policy gaps are included; these counts are not product coverage percentages. <a href="data/priority-counts.json">Exact chart data</a> | <a href="data/development-findings.json">Complete ledger</a>.</figcaption></figure><h3>First actions</h3><ol>'+''.join('<li>'+esc(x)+'</li>' for x in content['first_actions'])+'</ol><details><summary>Priority definitions</summary>'+''.join('<p><strong>'+p+':</strong> '+esc(s)+'</p>' for p,s in content['priorities'].items())+'</details></section>'
    body+='<section id="fixes"><h2>Which fixes are small and likely to matter?</h2><p>Actual production patches have been prepared in <strong>39 local branches for 38 findings</strong>: 35 Bonsai branches and four SDK branches, including one paired upload companion. No branch or PR has been published. Candidate status does not remove any issue from this development-baseline catalog.</p><p>'+esc(review['assessment_basis'])+'</p><p>'+esc(review['selection_rule'])+'</p><p><strong>Privacy P0 remains conditional:</strong> the candidate rejects new private-marked creation. Existing private-marked records remain readable across accounts; this is partial containment, not a complete ACL fix.</p><figure><picture><source media="(max-width:650px)" srcset="assets/patch-sizes-mobile.svg" width="280" height="158"><img class="chart" src="assets/patch-sizes.svg" width="480" height="158" alt="Local production patch sizes by added plus removed lines"></picture><figcaption>Figure 2. Added plus removed production lines per local candidate, grouped by size. Denominator: 39 branches, including the paired SDK companion. Counts use each stated base; prerequisites are additional. Line count is not a complexity or risk score. <a href="data/patch-size-counts.json">Exact data</a> | <a href="data/local-pr-catalog.json">Measured branch catalog</a>.</figcaption></figure><p><strong>Suggested review order:</strong> the role boundary and small deterministic preservation/filtering failures first; then feature-specific paths used in this installation. Concurrent-save and retry failures depend more on collaboration and network conditions. All 55 findings below have trigger and scope assessments; P2/P3 scopes are estimates without separate branches.</p><p><strong>Checks:</strong> all 39 candidate heads passed 91 focused checks. The combined candidates passed 35 API, 24 frontend and five SDK regressions, TypeScript checking and a production webpack build. Browser fixtures use real DataTables plugins and generic local rows. This does not establish live ingestion or diagnostic correctness.</p><p><strong>Dependencies:</strong> three candidates are based on prerequisite branches. The Kleborate change has an app/SDK pair. Two overlapping areas require small import/line unions when combined; the affected PR bodies document them.</p><div class="actions"><a class="primary" href="prs/index.html">Review local PR candidates</a><a href="data/candidate-verification.json">Pinned verification ledger</a></div></section>'
    for priority in ['P0','P1','P2','P3']:
        body+='<section id="'+priority.lower()+'"><h2>'+priority+' / '+str(counts[priority])+' known items</h2>'
        for item in ledger['findings']:
            if item['priority']!=priority:continue
            a=item['fix_assessment']
            candidate_links='; '.join('<a href="prs/'+c['id'].lower()+'.html"><code>'+esc(c['branch'])+'</code></a> ('+esc(c['repository'])+', base <code>'+esc(c['base_ref'])+'</code>)' for c in item['local_candidates'])
            assessment='<div class="assessment"><p><strong>Normal trigger / '+esc(a['exposure'])+':</strong> '+esc(a['normal_workflow'])+'</p><p><strong>Minimal fix:</strong> '+esc(a['minimal_fix'])+' '+esc(patch_size(item))+'</p><p><strong>Review assessment:</strong> '+esc(a['review_band'])+'. '+esc(a['caveat'])+'</p>'
            if candidate_links:assessment+='<p><strong>Actual local candidate:</strong> '+candidate_links+'. Exact diffs, dependencies and focused checks are linked there.</p>'
            assessment+='</div>'
            body+='<article class="finding" id="'+item['id']+'"><span class="priority '+priority.lower()+'">'+priority+'</span><span class="id">'+item['id']+'</span><h3>'+esc(item['title'])+'</h3><p>'+esc(item['observed'])+'</p><p><strong>Urgency:</strong> '+esc(item['why'])+'</p>'+assessment+'<p><strong>Acceptance:</strong> '+esc(item['acceptance'])+'</p><p class="evidence">'+esc(item['baseline_basis'])+'.</p><details><summary>Baseline source and saved evidence</summary><p class="note">Source IDs: '+esc(', '.join(item['source_ids']))+'. Full revisions and source hashes are recorded in the <a href="data/baseline-source-audit.json">source audit</a>.</p>'
            for index in item['source_checks']:
                check=source_audit['source_checks'][index];body+='<p class="note">'+esc(check['repository']+' '+check['revision'][:8]+' / '+check['path']+':'+str(check['line']))+'</p><pre class="source">'+esc(check['excerpt'])+'</pre>'
            body+='<div class="links">'+''.join('<a href="evidence/'+relative+'">'+esc(relative)+'</a>' for relative in item['evidence_documents'])+'</div></details></article>'
        body+='</section>'
    body+='<section class="screens" id="screenshots"><h2>Original baseline screenshots</h2>'+''.join('<figure><h3>'+esc(item['title'])+'</h3><a href="assets/'+path.name+'" target="_blank" rel="noopener"><img src="assets/'+path.name+'" alt="'+esc(item['title'])+'" loading="lazy"></a><figcaption>'+esc(item['caption'])+' Tap for the original PNG.</figcaption></figure>' for item,path in zip(content['screenshots'],images))+'</section>'
    body+='<section id="limits"><h2>Evidence strength and limits</h2><ul>'+''.join('<li><strong>'+esc(k)+':</strong> '+str(v)+' items.</li>' for k,v in ledger['counts_by_basis'].items())+'</ul><p class="note">Source-traced items were reproduced on later layered candidates. Their failure mechanisms were inspected at the pinned baseline; they were not all replayed in a fresh full baseline deployment.</p><ul>'+''.join('<li>'+esc(x)+'</li>' for x in content['limits'])+'</ul><p><a href="technical.html">Technical note and reproduction commands</a> | <a href="provenance.json">Report provenance and hashes</a></p></section></main><footer>Development baseline 21eccf7 / SDK 5789a9c. Local fix status does not affect this report. <a href="#answer">Back to summary</a>.</footer>'
    (output/'index.html').write_text(html_page(content['title'],header+body))
    technical='<header><p class="eyebrow">TECHNICAL NOTE / DEVELOPMENT BASELINE</p><h1>Attribution, scope and reproducibility</h1><p><a href="index.html">Return to known development issues</a></p></header><main><section><h2>Target and counting</h2><p>Bonsai <code>'+content['development_commit']+'</code>; recorded SDK <code>'+content['sdk_commit']+'</code>. The original test context pins both revisions. No remote fetch was performed.</p><p>'+esc(content['counting_rule'])+'</p><p>The former ledger had 57 consolidated items. The local-only sidebar regression and explained failed-QC case were removed, leaving 55. Source IDs and the original alias consolidation remain traceable; fix-status fields do not enter this catalog or its priority counts.</p></section><section><h2>Evidence basis</h2><ul>'+''.join('<li>'+esc(k)+': '+str(v)+'</li>' for k,v in ledger['counts_by_basis'].items())+'</ul><p>Original observations were made before the application fixes. Three parser items were tested against the pinned, unpatched SDK. The new isolated checks mount the extracted baseline application and SDK source in a network-disabled container. The real role/JWT code is used with user lookup and the downstream service stubbed. Generic inventory CSV cells and deterministic in-memory metadata/comment races exercise baseline code without the live database.</p><p>The remaining items were observed on layered candidates and inspected against Git blobs at the baseline. The source audit records file hashes, line anchors and excerpts. This supports attribution of the mechanism, rather than claiming a new full baseline browser reproduction for every row. The two later CSV observations also use unchanged export configuration and an unchanged dependency lockfile. Spreadsheet formula execution remains untested.</p><div class="links"><a href="data/baseline-source-audit.json">Source audit</a><a href="evidence/'+AUDIT+'/isolated-baseline-final.json">Isolated baseline results</a><a href="evidence/'+AUDIT+'/permission-gate-baseline.json">Baseline role-boundary results</a></div></section><section><h2>Reproduce and inspect</h2><p>Authored content: <code>docs/local-testing/development-review-content.json</code>. Builder: <code>scripts/build_development_review.py</code>. Generic checks: <code>scripts/check_development_baseline.py</code> and <code>scripts/check_release_permission_gate.py</code>.</p><p>Extract the recorded Git revisions before running the check scripts; use a container with <code>--network none</code>, the baseline API at <code>/app/api/bonsai_api</code>, the baseline SDK at its package path, and the saved generic test dependencies. Do not point these audit commands at the running source overlays.</p><p><code>python scripts/build_development_review.py --run-dir ~/data/codex/bonsai/runs/2026-11-06-species-ui --output ~/data/codex/bonsai/docs/development-findings/development</code></p><p>Optional publication of the report source branch is performed by the user: <code>git -C /home/jakob/src/codex/bonsai push -u origin fix/critical-ui-release-pass</code>.</p><p>ReportLab and Lato fonts are required. Generated figures, ledgers, PDF and page renders stay on the external data drive. Only explicit JSON, original PNG evidence and the requested review bodies/production diffs are published; raw browser DOM, credentials, logs and database payloads are excluded.</p></section><section><h2>Preservation</h2><p>The running patched instance was not switched to development. No live records, analyses or decisions were changed for this report. The earlier patched-candidate report is preserved separately. No Git push is performed.</p><p><a href="provenance.json">Authoring and artifact hashes</a></p></section></main>'
    technical=technical.replace('<section><h2>Preservation</h2>', '<section><h2>Local minimal-fix assessment</h2><p>Authored trigger and scope judgments are in <code>docs/local-testing/fix-assessments.json</code>. Per-PR bodies and the measured branch catalog are in <code>docs/local-testing/minimal-prs/</code>. Workflow exposure is an inference; no production telemetry or real JASEN examples were available. Severity remains independent of whether a local candidate exists.</p><p>Production-only branches were created without switching the live checkout. Checks extract immutable branch trees and use isolated containers or Chromium with generic local fixtures. A disposable network-isolated MongoDB instance checked the two EMM projection paths against generic strings; the running database was not contacted. Parser checks use frozen literal inputs without running an analysis tool.</p><p>The three browser checks first reproduce the baseline failure and then check the individual candidate using the same installed DataTables dependencies. The remaining focused checks cover 39 total candidate heads and 91 passed checks. The composed candidate worktrees passed 35 API, 24 frontend and five SDK checks, TypeScript checking and a production build. Two manual overlap resolutions retain both changes: the metadata model imports and the null-safe decision-filter line.</p><p>Run <code>python3 scripts/verify_minimal_prs.py</code>, then <code>scripts/check_minimal_pr_browser.py</code> with the saved Selenium environment. The first command marks three entries as browser-pending; the second supplies their browser results. <code>python3 scripts/check_minimal_pr_integration.py --validate</code> repeats the already-composed checks. <code>scripts/build_minimal_pr_catalog.py</code> pins successful evidence and produces local review bodies.</p><p>The privacy branch is partial containment for new public-only creation, not ACL enforcement on existing records. The Kleborate API/SDK pair is transport-only verification. No live ingestion, curation writes, clustering or external biological data acquisition occurred in this pass. The full CI matrix, including unchanged services and Python 3.12, was not rerun. Pylint passed the CI score threshold on the composed API (9.09/10) and frontend (9.56/10). Earlier completed reports remain archived; the earlier patched-candidate report remains separately available.</p><p><a href="prs/index.html">Review bodies and exact patches</a> | <a href="data/local-pr-catalog.json">Branch and validation catalog</a></p></section><section><h2>Preservation</h2>')
    (output/'technical.html').write_text(html_page('Bonsai development issue methods',technical))
    provenance={'created_at':datetime.now(timezone.utc).isoformat(),'target':{'development':content['development_commit'],'sdk':content['sdk_commit']},'report_source_commit':subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),'counts_by_priority':counts,'counts_by_basis':ledger['counts_by_basis'],'excluded':ledger['excluded'],'evidence':evidence,'authoring_sources':{str(p.relative_to(REPO)):digest(p) for p in [CONTENT,ASSESSMENTS,PR_CATALOG,Path(__file__),REPO/'scripts/build_minimal_pr_catalog.py',REPO/'scripts/check_minimal_pr_browser.py',REPO/'scripts/prepare_minimal_prs.py',REPO/'scripts/minimal_pr_fixes.py',REPO/'scripts/verify_minimal_prs.py',REPO/'scripts/check_development_baseline.py',REPO/'scripts/check_release_permission_gate.py',REPO/'scripts/build_release_review.py']},'public_artifacts':{str(p.relative_to(output)):{'sha256':digest(p),'bytes':p.stat().st_size} for p in output.rglob('*') if p.is_file() and p.name!='provenance.json'}}
    write_json(output/'provenance.json',provenance)
    print(json.dumps({'html':str(output/'index.html'),'pdf':str(pdf),'issues':ledger['issue_count'],'priorities':counts,'basis':ledger['counts_by_basis']}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir',type=Path,default=DATA/'runs/2026-11-06-species-ui')
    parser.add_argument('--output',type=Path,default=DATA/'docs/development-findings/development')
    args=parser.parse_args();build(args.run_dir,args.output)
