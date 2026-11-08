#!/usr/bin/env python3
"""Consolidate the requested final software-test report without changing old reports.

Authored prose lives in docs/local-testing/final-review-content.json. Existing
baseline findings, assessments and candidate evidence are read in place. Generated
PDF, figures, copied screenshots and small public evidence snapshots stay on the
external data drive. No application, database or biological workflow is run.
"""
from collections import Counter
import csv
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re
import shutil
import subprocess

from reportlab.graphics import renderSVG
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, KeepTogether, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)


REPO = Path(__file__).resolve().parents[1]
BASE_REPO = Path('/home/jakob/src/codex/bonsai')
DATA = Path('/home/jakob/data/codex/bonsai')
JDATA = Path('/home/jakob/data/codex/jasen')
SITE = DATA / 'docs/development-findings'
OUTPUT = SITE / 'final'
RUN = DATA / 'runs/2026-11-08-final-report'
PILOT = JDATA / 'runs/2026-11-08-bonsai-reference-pilot'
HUB = JDATA / 'runs/2026-11-08-organism-coverage'
AUDIT = DATA / 'runs/2026-11-08-parser-fixture-audit'
CONTENT = REPO / 'docs/local-testing/final-review-content.json'
URL = 'http://100.90.51.21:8001/final/'
INK, MUTED, TEAL, LINE = '#193740', '#536b73', '#23685f', '#d8e2e2'
PRIORITY = {'P0': '#a73145', 'P1': '#b66220', 'P2': '#366ba0', 'P3': '#6e7c86'}
TOKEN = re.compile(rb'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.')


def read(path):
    return json.loads(Path(path).read_text())


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode()
    if TOKEN.search(payload):
        raise ValueError(f'Token-shaped content refused: {path}')
    path.write_bytes(payload)


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


def preserved_reports():
    paths = [p for p in SITE.rglob('*') if p.is_file() and not p.is_relative_to(OUTPUT)]
    paths += [p for p in (HUB / 'docs').rglob('*') if p.is_file()]
    return {str(p): digest(p) for p in sorted(set(paths))}


def extra_candidate(source, repository, branch, head, base, dependencies, validation):
    production = []
    for row in git(repository, 'diff', '--numstat', base, head).splitlines():
        added, removed, path = row.split('\t', 2)
        if path.startswith(('tests/', 'test/')):
            continue
        if path.startswith(('api/', 'src/', 'prp/', 'modules/')):
            production.append({'path': path, 'added': int(added), 'removed': int(removed)})
    return {'id': source, 'repository': {'index_auth': 'Bonsai', 'read_pairs': 'SDK',
            'jasen_quote': 'JASEN', 'prp_companion': 'PRP', 'sdk_kaptive': 'SDK'}[source],
        'repository_path': str(repository), 'branch': branch, 'head': head,
        'base_commit': base, 'dependencies': dependencies, 'paired_candidates': [],
        'production_added': sum(x['added'] for x in production),
        'production_removed': sum(x['removed'] for x in production), 'files': production,
        'verification': {'status': 'PASS', 'summary': validation},
        'policy_condition': None, 'merge_note': None}


def assemble(content):
    original = read(SITE / 'development/data/development-findings.json')
    catalog = read(BASE_REPO / 'docs/local-testing/minimal-prs/catalog.json')
    assert len(original['findings']) == 55 and len(catalog['candidates']) == 39
    candidates = []
    for old in catalog['candidates']:
        c = dict(old)
        c['repository_path'] = str(BASE_REPO / 'bonsai-sdk' if c['repository'] == 'SDK' else BASE_REPO)
        candidates.append(c)
    auth = read(PILOT / 'bonsai/index-auth-fix.json')
    pairs = read(PILOT / 'bonsai/read-pair-count-fix.json')
    quote = read(PILOT / 'pipeline-status.json')['local_producer_patch']
    kfix = read(HUB / 'cases/klebsiella/saved-report-ingestion/local-fixes.json')
    sources = {x['candidate_source']: x for x in content['new_findings'] if x['candidate_source']}
    new_candidates = {
        'index_auth': extra_candidate('index_auth', BASE_REPO, auth['branch'], auth['head'],
            auth['base_commit'], ['ACCOUNT-ROLE-PERMISSIONS'], sources['index_auth']['validation']),
        'read_pairs': extra_candidate('read_pairs', BASE_REPO / 'bonsai-sdk', pairs['branch'],
            pairs['head'], pairs['base_commit'], [], sources['read_pairs']['validation']),
        'jasen_quote': extra_candidate('jasen_quote', Path(quote['path']), quote['branch'],
            quote['head'], quote['upstream_commit'], [], sources['jasen_quote']['validation']),
        'prp_companion': extra_candidate('prp_companion', Path(kfix['PRP']['repository']),
            kfix['PRP']['branch'], kfix['PRP']['head'], kfix['PRP']['base'],
            ['KLEBORATE-UPLOAD-422', 'KLEBORATE-CLIENT-COMPANION'], sources['prp_companion']['validation']),
        'sdk_kaptive': extra_candidate('sdk_kaptive', BASE_REPO / 'bonsai-sdk',
            kfix['SDK']['branch'], kfix['SDK']['head'], kfix['SDK']['base'], [],
            sources['sdk_kaptive']['validation']),
    }
    for key, c in new_candidates.items():
        c['id'] = sources[key]['id']
        candidates.append(c)
    verified = []
    for c in candidates:
        actual = git(c['repository_path'], 'rev-parse', 'refs/heads/' + c['branch'])
        if actual != c['head']:
            raise ValueError(f"Branch moved: {c['repository']} {c['branch']}")
        measured = []
        for row in git(c['repository_path'], 'diff', '--numstat', c['base_commit'], c['head']).splitlines():
            a, r, path = row.split('\t', 2)
            if path.startswith(('api/', 'frontend/', 'src/', 'prp/', 'modules/')):
                measured.append((int(a), int(r), path))
        if (sum(x[0] for x in measured), sum(x[1] for x in measured)) != (c['production_added'], c['production_removed']):
            raise ValueError(f"Production diff changed: {c['branch']}")
        c['local_ref_verified'] = True
        verified.append({'repository': c['repository'], 'repository_path': c['repository_path'],
            'branch': c['branch'], 'head': actual, 'base': c['base_commit'],
            'production_added': c['production_added'], 'production_removed': c['production_removed'],
            'production_files': len(measured)})
    by_id = {c['id']: c for c in candidates}
    issues = []
    for row in original['findings']:
        a = row['fix_assessment']
        cs = [by_id[row['id']]] if row['id'] in by_id else []
        if row['id'] == 'KLEBORATE-UPLOAD-422':
            cs.append(by_id['KLEBORATE-CLIENT-COMPANION'])
        validation = '; '.join(f"{c['verification']['passed']} focused checks passed ({c['verification']['method']})" for c in cs)
        issues.append({
            'id': row['id'], 'priority': row['priority'], 'title': row['title'],
            'area': row['area'], 'scope': 'Pinned development baseline',
            'observed': row['observed'], 'why': row['why'], 'acceptance': row['acceptance'],
            'normal_workflow': a['normal_workflow'], 'minimal_fix': a['minimal_fix'],
            'caveat': a.get('caveat'), 'basis': row['baseline_basis'],
            'review_band': a['review_band'], 'candidates': cs, 'test_data_only': False,
            'validation': validation or 'No separate candidate verification in the P0/P1 preparation pass.',
            'evidence': ['../development/#' + row['id']],
            'original_evidence_documents': row['evidence_documents'],
        })
    for authored in content['new_findings']:
        row = dict(authored)
        key = row.pop('candidate_source')
        row.update({'scope': 'Later fixture finding' if row.get('test_data_only') else 'Later integration finding',
            'candidates': [new_candidates[key]] if key else [], 'caveat': None,
            'test_data_only': row.get('test_data_only', False)})
        issues.append(row)
    issues.sort(key=lambda x: (x['priority'], 0 if x['scope'] == 'Pinned development baseline' else 1))
    assert len(issues) == 64 and len({x['id'] for x in issues}) == 64
    assert len(candidates) == 44 and sum(bool(x['candidates']) for x in issues) == 43
    assert [x['id'] for x in issues if x['priority'] in {'P0', 'P1'} and not x['candidates']] == [
        'MISSING-ANALYSIS-NEGATIVE-SUMMARY', 'KLEBORATE-SUMMARY-DISPATCH']
    counts = dict(Counter(x['priority'] for x in issues))
    assert counts == {'P0': 4, 'P1': 41, 'P2': 16, 'P3': 3}, counts
    context = {'development_commit': original['development_commit'], 'sdk_baseline': original['sdk_commit'],
        'local_development_ref': git(BASE_REPO, 'rev-parse', 'development'),
        'report_source_branch': git(REPO, 'branch', '--show-current'),
        'report_source_parent': git(REPO, 'rev-parse', 'HEAD'),
        'pilot': read(PILOT / 'bonsai/source-context.json'),
        'parser_audit': read(AUDIT / 'result.json')['source_context'],
        'jasen_baseline': read(PILOT / 'pipeline-status.json')['upstream_commit'],
        'prp_baseline': kfix['PRP']['base'],
        'baseline_evidence_counts': original['counts_by_basis'],
        'remote_fetch_performed': False, 'git_push_performed': False,
        'app_or_database_mutation_performed': False, 'new_sequence_processing_performed': False}
    return issues, candidates, verified, counts, context, catalog


def priority_figure(issues):
    d = Drawing(500, 153)
    for i, p in enumerate(PRIORITY):
        rows = [x for x in issues if x['priority'] == p]
        prepared = sum(bool(x['candidates']) for x in rows)
        y = 122 - i * 33
        d.add(String(0, y + 6, p, fontName='Lato-Bold', fontSize=11, fillColor=colors.HexColor(PRIORITY[p])))
        width = 325 * len(rows) / 41
        d.add(Rect(35, y, width, 18, fillColor=colors.HexColor('#e2e8e8'), strokeColor=None))
        if prepared:
            d.add(Rect(35, y, width * prepared / len(rows), 18, fillColor=colors.HexColor(TEAL), strokeColor=None))
        d.add(String(370, y + 5, f'{len(rows)} findings / {prepared} with candidates',
            fontName='Lato', fontSize=9, fillColor=colors.HexColor(INK)))
    return d


def regression_figure(audit):
    rows = [('SDK parser tests', 196, 196), ('PRP tests', 46, 46),
            ('Corrected contract checks', 714, 714), ('Saved-file checks', 180, 180)]
    assert audit['combined_regression']['sdk_parser_tests']['tests'] == 196
    d = Drawing(500, 153)
    for i, (label, passed, total) in enumerate(rows):
        y = 125 - i * 33
        d.add(String(0, y + 6, label, fontName='Lato', fontSize=9.5, fillColor=colors.HexColor(INK)))
        d.add(Rect(190, y, 230, 17, fillColor=colors.HexColor(TEAL), strokeColor=None))
        d.add(String(430, y + 5, f'{passed}/{total}', fontName='Lato-Bold', fontSize=10, fillColor=colors.HexColor(INK)))
    return d


def mobile_figures(issues):
    priorities = Drawing(300, 240)
    regression = Drawing(300, 240)
    for i, priority in enumerate(PRIORITY):
        rows = [x for x in issues if x['priority'] == priority]
        prepared = sum(bool(x['candidates']) for x in rows)
        y = 207 - i * 57
        priorities.add(String(0, y + 14, f'{priority}: {len(rows)} findings / {prepared} with candidates',
            fontName='Lato-Bold', fontSize=11.5, fillColor=colors.HexColor(INK)))
        width = 290 * len(rows) / 41
        priorities.add(Rect(0, y - 11, width, 17, fillColor=colors.HexColor('#e2e8e8'), strokeColor=None))
        if prepared:
            priorities.add(Rect(0, y - 11, width * prepared / len(rows), 17,
                fillColor=colors.HexColor(TEAL), strokeColor=None))
    for i, (label, count) in enumerate([('SDK parser tests', 196), ('PRP tests', 46),
            ('Corrected contract checks', 714), ('Saved-file checks', 180)]):
        y = 207 - i * 57
        regression.add(String(0, y + 14, f'{label}: {count}/{count}', fontName='Lato-Bold',
            fontSize=11.5, fillColor=colors.HexColor(INK)))
        regression.add(Rect(0, y - 11, 290, 17, fillColor=colors.HexColor(TEAL), strokeColor=None))
    return priorities, regression


def styles():
    for name, path in [('Lato', 'Lato-Regular.ttf'), ('Lato-Bold', 'Lato-Bold.ttf'), ('Lato-Italic', 'Lato-Italic.ttf')]:
        pdfmetrics.registerFont(TTFont(name, '/usr/share/fonts/truetype/lato/' + path))
    pdfmetrics.registerFontFamily('Lato', normal='Lato', bold='Lato-Bold', italic='Lato-Italic', boldItalic='Lato-Bold')
    return {
        'body': ParagraphStyle('Body', fontName='Lato', fontSize=9.5, leading=13, spaceAfter=6, textColor=colors.HexColor(INK)),
        'small': ParagraphStyle('Small', fontName='Lato', fontSize=8.2, leading=11, spaceAfter=5, textColor=colors.HexColor(MUTED)),
        'title': ParagraphStyle('Title', fontName='Lato-Bold', fontSize=25, leading=29, spaceAfter=14, textColor=colors.HexColor(INK)),
        'h1': ParagraphStyle('H1', fontName='Lato-Bold', fontSize=18, leading=22, spaceBefore=10, spaceAfter=10, textColor=colors.HexColor(TEAL), keepWithNext=True),
        'h2': ParagraphStyle('H2', fontName='Lato-Bold', fontSize=12, leading=15, spaceBefore=5, spaceAfter=5, textColor=colors.HexColor(INK), keepWithNext=True),
        'code': ParagraphStyle('Code', fontName='Lato', fontSize=8.2, leading=11, spaceAfter=5, textColor=colors.HexColor(INK)),
        'lead': ParagraphStyle('Lead', fontName='Lato', fontSize=11.5, leading=16, spaceAfter=10, textColor=colors.HexColor(INK)),
    }


def size(c):
    return f"+{c['production_added']}/-{c['production_removed']}; {len(c['files'])} production file(s)"


def branch_text(issue):
    if not issue['candidates']:
        return 'None prepared (open; estimated fix scope only)'
    return '; '.join(f"{c['repository']}: {c['branch']} ({c['head'][:10]})" for c in issue['candidates'])


def pdf_report(content, issues, candidates, counts, drawings, loaded, context, s):
    story = []
    def p(text, style='body'):
        return Paragraph(text, s[style])
    def text(value, style='body'):
        story.append(p(escape(value), style))
    def heading(value):
        story.append(p(escape(value), 'h1'))
    def link(label, target):
        return f'<a href="{escape(target, quote=True)}" color="{TEAL}">{escape(label)}</a>'
    text('FINAL SOFTWARE TEST REVIEW / ' + content['as_of'].upper(), 'small')
    text(content['title'], 'title')
    text(content['question'], 'h2')
    text(content['answer'], 'lead')
    story.append(drawings[0])
    text('Figure 1. Findings by recommended urgency. Teal marks findings with a separate local candidate; grey marks those without one. Denominator: 64 distinct findings, including one P2 fixture-only item. Prepared candidates are not merged fixes.', 'small')
    story.append(p(link('Exact issue and branch data', URL + 'data/issues.json') + ' | ' + link('Interactive report and evidence', URL), 'small'))
    text('55 pinned-baseline findings + 8 later product/integration findings + 1 fixture-provenance finding. 44 verified local branches cover 43 findings; 21 findings have no separate candidate. All 4 P0 and 39 of 41 P1 findings have candidates.', 'body')
    text('Target: Bonsai development 21eccf7; recorded SDK baseline 5789a9c. Later findings include PRP 2.0.0 and JASEN 1.4.1. Local fix status does not remove an issue from this report.', 'small')
    story.append(p(link('Issue register', URL + '#issues') + ' | ' + link('Branch register', URL + '#branches') + ' | ' + link('Methods and limits', URL + 'technical.html'), 'body'))

    story.append(PageBreak())
    heading('Suggested review order')
    for row in content['recommended_order']:
        story.append(p(escape(row['title']), 'h2'))
        text(row['text'])
        story.append(p('Related: ' + ', '.join(link(fid, URL + '#' + fid) for fid in row['issues']), 'small'))
    heading('Priority definitions')
    for priority, definition in read(BASE_REPO / 'docs/local-testing/development-review-content.json')['priorities'].items():
        story.append(p(f'<b>{priority}.</b> {escape(definition)}'))
    text('Workflow frequency is inferred from each observed trigger, not measured production telemetry. Exact production diffs are listed for prepared candidates; unimplemented changes are explicitly estimates.', 'small')

    story.append(PageBreak())
    heading('What was tested, and what passed?')
    text('The broad synthetic pass covered 80 records across eight assay names representing seven profiles, plus generic table workflows up to 125 records. Browser, API, role, metadata, concurrency, recovery, export and parser behavior were investigated. The original 39 candidate branches passed 91 focused checks; the recorded combined candidate build/API/frontend/SDK checks also passed.')
    story.append(drawings[1])
    text('Figure 2. Final offline regression on the locally patched SDK/uploader: 196 SDK tests, 46 PRP tests, 714 contract checks and 180 saved-file checks pass. These are different, overlapping check sets, not independent samples. Contract checks use a derived format-corrected copy; the original run had 694 passes and 20 fixture-format failures.', 'small')
    story.append(p(link('Exact parser-audit results', URL + 'data/parser-audit-results.json'), 'small'))
    text('Twenty old synthetic reports lacked the publisher Kaptive module prefix. Only a separate derived copy was corrected against the tagged 3.2.4 publisher format; original bytes and expected result values were preserved. This audit required no further production parser change.')
    text('Forty-eight saved files provide examples for all 22 registered parser keys. Six version labels remain explicitly unverified placeholders or format-family labels. Full live import/display coverage and independent expected values for every field are still incomplete.')
    heading('Native and saved-report integration')
    text('One E. coli K-12 laboratory-control raw-data run completed: 11 canonical analyses and 16 stored view descriptors. Six initial browser checks and eight additional fidelity checks passed after local fixes. Saved S. aureus: 11/13 checks pass. TB-profile numeric QC: 14/15. Kleborate: 4/4 imports and whole-envelope comparisons pass, while 29/43 functional checks pass; 14 failures remain in summary reading. These denominators overlap and must not be pooled as an accuracy estimate.')

    story.append(PageBreak())
    heading('Profile coverage and loaded results')
    text('The entries below are software profiles; two are broad genus buckets. Every profile had earlier synthetic coverage. Counts in this table describe only the newer isolated instance, which has seven records across four profiles.')
    rows = [[p('Profile', 'small'), p('Newer-instance results and limits', 'small')]]
    coverage = coverage_rows(loaded)
    for label, detail in coverage:
        rows.append([p(escape(label)), p(escape(detail))])
    t = Table(rows, colWidths=[108, 403], hAlign='LEFT', repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#edf3f2')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8), ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6), ('LINEBELOW', (0, 0), (-1, -1), .4, colors.HexColor(LINE))]))
    story.append(t)
    text('The four Kleborate scenarios reuse one primary/companion pair under two aliases and two companion states. The header-only companion control is deliberately synthetic and is not a coherent biological negative. No native TB or other-species producer validation is implied.', 'small')
    story.append(p(link('Loaded-result inventory and links', URL + '../organisms/'), 'small'))
    heading('Interpretation of the final state')
    text('The saved-fixture set is approaching diminishing returns. The latest screen added no production parser defect. Known display failures remain actionable, and independent saved outputs or import-lifecycle scenarios would add more information than repetitions of the same fixtures.')

    for priority in PRIORITY:
        story.append(PageBreak())
        heading(priority + ' findings')
        text({'P0': 'Access and privacy boundaries: review before ordinary-user or restricted-data release.',
              'P1': 'Blocked or misleading workflows: review before the affected workflow is released.',
              'P2': 'Deferred corrections and scope decisions, including one fixture-only finding.',
              'P3': 'Presentation, accessibility and export-policy follow-up.'}[priority], 'small')
        for issue in [x for x in issues if x['priority'] == priority]:
            flows = [p('<a name="' + issue['id'] + '"/>' + escape(issue['id']), 'small'),
                p(escape(issue['title']), 'h2'),
                p('<b>Observed.</b> ' + escape(issue['observed']) + ' <b>Impact.</b> ' + escape(issue['why'])),
                p('<b>Trigger.</b> ' + escape(issue['normal_workflow'])),
                p('<b>Minimal fix.</b> ' + escape(issue['minimal_fix']))]
            flows.append(p('<b>Suggested fix branch.</b> ' + escape(branch_text(issue)), 'code'))
            for c in issue['candidates']:
                detail = f"{c['repository']}: {size(c)}"
                if c['dependencies']:
                    detail += '; prerequisite: ' + ', '.join(c['dependencies'])
                if c['paired_candidates']:
                    detail += '; pair: ' + ', '.join(c['paired_candidates'])
                if c.get('policy_condition'):
                    detail += '; conditional: ' + c['policy_condition']
                flows.append(p(escape(detail), 'small'))
            if issue.get('caveat'):
                flows.append(p('<b>Review limit.</b> ' + escape(issue['caveat']), 'small'))
            flows.append(p('<b>Verification.</b> ' + escape(issue['validation']), 'small'))
            flows.append(p(escape(issue['scope'] + ' / ' + issue['basis']) + '. ' +
                link('Evidence and acceptance criteria', URL + '#' + issue['id']), 'small'))
            flows.append(Spacer(1, 11))
            story.append(KeepTogether(flows))

    story.append(PageBreak())
    heading('Selected screenshot evidence')
    text('Screenshots preserve the instance and stage at which the behavior was observed. Evidence from the patched integration instance is labelled separately from original development evidence. All issue entries link to their complete evidence.')
    for i, item in enumerate(content['screenshots']):
        if i and i % 2 == 0:
            story.append(PageBreak())
            heading('Screenshot evidence, continued')
        im = Image(str(OUTPUT / 'assets' / item['name']))
        scale = min(511 / im.imageWidth, 290 / im.imageHeight)
        im.drawWidth, im.drawHeight = im.imageWidth * scale, im.imageHeight * scale
        story.append(KeepTogether([p(escape(item['title']), 'h2'), im,
            p(escape(item['caption']) + ' ' + link('Full-resolution image', URL + 'assets/' + item['name']), 'small')]))

    story.append(PageBreak())
    heading('Local branch register')
    text('All 44 branch refs and their production diffs were checked against the recorded heads during report generation. Every branch is local; nothing was pushed. Repositories, base commits, complete heads, dependencies and file-level sizes are in the downloadable register.')
    story.append(p(link('Complete branch data', URL + 'data/branches.json') + ' | ' +
        link('CSV decision table', URL + 'data/issues.csv'), 'body'))
    for repository in ['Bonsai', 'SDK', 'PRP', 'JASEN']:
        rows = [c for c in candidates if c['repository'] == repository]
        story.append(p(f'{repository}: {len(rows)} branches', 'h2'))
        for c in rows:
            story.append(p(escape(c['branch']) + ' / ' + escape(c['head'][:10]) + ' / ' + escape(size(c)), 'code'))
    text('The SDK is nested at /home/jakob/src/codex/bonsai/bonsai-sdk. PRP is a separate repository. The JASEN quoting branch is in the external-data-drive producer checkout. Branches without prerequisites are generally based directly on the recorded repository baseline; exact bases are in branches.json.', 'small')

    story.append(PageBreak())
    heading('Species context')
    text('This is a short clinical orientation to the configured profile names. Disease context is independent of software-test coverage and is not a claim of diagnostic validation.')
    for row in content['species_context']:
        story.append(p(escape(row['profile']), 'h2'))
        urls = link('Clinical source', row['source'])
        if row.get('source2'):
            urls += ' / ' + link('Additional source', row['source2'])
        story.append(p(escape(row['context']) + ' ' + urls))

    story.append(PageBreak())
    heading('Scope, limits and handoff')
    for row in content['limits']:
        text(row)
    heading('Next-week handoff')
    for row in content['handoff']:
        text(row)
    story.append(p(link('Technical note and source context', URL + 'technical.html') + ' | ' +
        link('Preserved original development report', URL + '../development/'), 'small'))

    path = OUTPUT / 'output/pdf/bonsai-final-test-report.pdf'
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(str(path), pagesize=A4, leftMargin=42, rightMargin=42,
        topMargin=44, bottomMargin=43, title=content['title'], author='Bonsai software test review',
        subject=content['question'], allowSplitting=1)
    def page(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor(LINE))
        canvas.line(42, 30, A4[0] - 42, 30)
        canvas.setFont('Lato', 8)
        canvas.setFillColor(colors.HexColor(MUTED))
        canvas.drawString(42, 18, 'Bonsai / pinned development review / 8 November 2026')
        canvas.drawRightString(A4[0] - 42, 18, str(document.page))
        canvas.restoreState()
    doc.addPageTemplates([PageTemplate(id='main', frames=[Frame(42, 43, A4[0] - 84, A4[1] - 87,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=page)])
    doc.build(story)
    return path


def coverage_rows(loaded):
    profiles = {x['key']: x for x in loaded['profiles']}
    assert sum(x['record_count'] for x in profiles.values()) == 7
    return [
        ('E. coli', '1 native K-12 control; 11 analyses / 16 descriptors. One paired Illumina raw-data workflow.'),
        ('S. aureus', '1 mixed saved-report software record; 4 analyses / 4 descriptors. QC and stored typing fidelity; summary gaps remain.'),
        ('Klebsiella', '4 software scenarios; 1 analysis / 11 descriptors each. Both aliases, companion present/header-only; import passes, reading failures remain.'),
        ('S. pyogenes', 'No newer-instance record. Earlier synthetic parser/browser coverage only; no independent native run.'),
        ('Other Streptococcus', 'No newer-instance record. Earlier synthetic coverage only; the genus bucket is not validation of every member species.'),
        ('Other Staphylococcus', 'No newer-instance record. Earlier synthetic coverage only; the genus bucket is not validation of every member species.'),
        ('M. tuberculosis', '1 saved numeric-QC record; 2 analyses / 2 descriptors. No native sequence processing or biological-result report.')]


CSS = '''
:root{color-scheme:light;--ink:#193740;--teal:#23685f;--line:#d8e2e2}*{box-sizing:border-box}
body{margin:0;background:#f2f6f5;color:var(--ink);font:16px/1.55 system-ui,sans-serif}
main{max-width:1080px;margin:auto;padding:24px}header,section{background:#fff;border:1px solid var(--line);border-radius:12px;padding:28px;margin-bottom:20px}
h1{font-size:34px;line-height:1.18;margin:.3em 0 .6em}h2{font-size:24px;line-height:1.25;color:var(--teal)}h3{font-size:19px;line-height:1.3}
a{color:#05647b}a:hover{text-decoration-thickness:2px}.eyebrow{letter-spacing:.08em;font-size:12px;font-weight:700;color:#536b73}.lead{font-size:19px;line-height:1.5}
.actions,nav{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0}.actions a,nav a{padding:8px 12px;border:1px solid var(--line);border-radius:6px;text-decoration:none}.primary{background:var(--teal);color:#fff}
.notice{border-left:4px solid #b66220;padding:10px 15px;background:#fbf7ee}.muted,figcaption,small{color:#536b73;font-size:13px}
figure{margin:18px 0}figure img{max-width:100%;height:auto;border:1px solid var(--line)}.chart{max-width:720px;width:100%;border:0}
code{font:13px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere;white-space:normal}p,td,th,li{overflow-wrap:anywhere}
.issue{border-top:1px solid var(--line);padding:22px 0 12px;scroll-margin-top:12px}.issue h3{margin:.3em 0 .7em}.issue p{margin:.6em 0}
.badge{display:inline-block;font-size:12px;font-weight:700;border-radius:4px;padding:2px 7px;background:#edf3f2}.p0{color:#a73145}.p1{color:#b66220}.p2{color:#366ba0}.p3{color:#6e7c86}
table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:left;vertical-align:top;border-bottom:1px solid var(--line);padding:10px}th{background:#edf3f2}.table{overflow-x:auto}.branch-list{padding-left:20px}
details{margin:12px 0}summary{cursor:pointer;color:#05647b}.stats{display:flex;gap:18px;flex-wrap:wrap}.stats b{font-size:26px;display:block}.stats span{font-size:13px;color:#536b73}
@media(max-width:600px){main{padding:10px}header,section{padding:18px}h1{font-size:28px}h2{font-size:22px}.lead{font-size:17px}td,th{padding:8px}.actions a,nav a{padding:7px 9px}}
@media print{body{background:white}main{padding:0;max-width:none}header,section{border:0;padding:0}.actions,nav{display:none}.issue,figure{break-inside:avoid}details>*{display:block}}
'''


def render_html(content, issues, candidates, counts, loaded, context):
    e = escape
    def a(label, href):
        return f'<a href="{e(href, quote=True)}">{e(label)}</a>'
    def paras(rows):
        return ''.join('<p>' + e(x) + '</p>' for x in rows)
    def shell(title, main):
        return f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)}</title><style>{CSS}</style></head><body><main>{main}</main></body></html>'
    figures = '''<figure><img class="chart" src="assets/priorities.svg" alt="Four P0, 41 P1, 16 P2 and three P3 findings; 43 findings have local candidates"><figcaption>Figure 1. Distinct findings by recommended urgency; teal means a separate local candidate exists, grey means none is prepared. Denominator: 64 findings, including one P2 fixture-only item. Candidate preparation does not mean a fix is on development. <a href="data/issues.json">Exact issue data</a>.</figcaption></figure>'''
    header = f'''<header><p class="eyebrow">BONSAI / FINAL SOFTWARE TEST REVIEW / {e(content['as_of'].upper())}</p><h1>{e(content['question'])}</h1><p class="lead">{e(content['answer'])}</p>{figures}<p>55 pinned-baseline findings + 8 later product/integration findings + 1 fixture-provenance finding. <strong>44 verified local branches cover 43 findings.</strong> Two later P1 display issues remain without a prepared candidate.</p><p class="notice">Target: development <code>21eccf7</code> and recorded SDK <code>5789a9c</code>. Later integration findings retain separate attribution. Findings remain listed even when a local fix exists; no merge, push or deployment is implied.</p><div class="actions"><a class="primary" href="output/pdf/bonsai-final-test-report.pdf" download>Download final PDF</a><a href="data/issues.csv" download>Download issue/branch CSV</a><a href="technical.html">Methods and limits</a><a href="../development/">Original development report</a><a href="../organisms/">Loaded results</a></div><nav><a href="#review-order">Review order</a><a href="#coverage">Coverage</a><a href="#issues">Issue register</a><a href="#branches">Fix branches</a><a href="#screenshots">Screenshots</a><a href="#handoff">Handoff</a></nav></header>'''
    order = '<section id="review-order"><h2>Suggested review order</h2>'
    for row in content['recommended_order']:
        order += f'<h3>{e(row["title"])}</h3><p>{e(row["text"])}</p><p class="muted">Related: ' + ', '.join(a(fid, '#' + fid) for fid in row['issues']) + '</p>'
    order += '<p class="muted">Workflow exposure is inferred from the observed trigger, not measured production frequency. Priorities express recommended release urgency. Exact production sizes apply to prepared candidates; unimplemented fixes remain estimates.</p></section>'
    coverage = '''<section id="coverage"><h2>What was tested, and what passed?</h2><p>The broad synthetic pass covered <strong>80 records across eight assay names representing seven profiles</strong>, with generic table workflows up to 125 records. The original 39 local candidates passed 91 focused checks and the recorded combined build/API/frontend/SDK checks.</p><figure><img class="chart" src="assets/regression.svg" alt="196 SDK tests, 46 PRP tests, 714 corrected contract checks and 180 saved-file checks pass"><figcaption>Figure 2. Final offline regression on the patched SDK/uploader. These are overlapping check sets, not independent biological samples. The original contract run had 694 passes and 20 fixture-format failures; the separate corrected copy passes 714/714. <a href="data/parser-audit-results.json">Exact results, pinned revisions and limitations</a>.</figcaption></figure><p>Forty-eight saved files provide examples for all 22 registered parser keys. Twenty old synthetic reports were corrected only in a separate derived copy using the tagged publisher format; originals and expected values were preserved. Six fixture version labels remain explicitly unverified. This last audit required no further production parser fix.</p><p>The single native E. coli K-12 raw-data run stored 11 canonical analyses and 16 view descriptors; 6 initial browser checks and 8 additional fidelity checks passed after local fixes. Saved S. aureus checks: 11/13; TB-profile numeric-QC checks: 14/15. Kleborate: 4/4 imports and envelope comparisons pass, but 29/43 functional checks pass, leaving 14 summary-reading failures. These denominators overlap and are not an accuracy estimate.</p><h3>Newer isolated instance</h3><p>All profiles had earlier synthetic coverage. The following counts describe only the newer instance: seven records across four profiles.</p><table><thead><tr><th>Profile</th><th>Loaded results and limits</th></tr></thead><tbody>'''
    coverage += ''.join(f'<tr><td>{e(label)}</td><td>{e(detail)}</td></tr>' for label, detail in coverage_rows(loaded))
    coverage += '</tbody></table><p class="muted">Four Kleborate scenarios reuse one saved report pair. Its header-only companion is a deliberately synthetic software control, not a coherent biological negative. The TB-profile addition is numeric QC only. <a href="../organisms/">Exact loaded-record inventory and live record links</a>.</p><p>The saved fixture set is approaching diminishing returns. The latest audit added no production parser defect; known display failures and import-lifecycle gaps remain.</p></section>'
    register = '<section id="issues"><h2>Prioritized issue register</h2><p>Every finding includes a branch reference or an explicit statement that none is prepared. Acceptance criteria and evidence appear under each issue. A branch can require a prerequisite or a companion change in another repository.</p><nav>'
    register += ''.join(a(f'{p}: {counts[p]}', '#' + p) for p in PRIORITY) + '</nav>'
    for priority in PRIORITY:
        register += f'<h2 id="{priority}" class="{priority.lower()}">{priority} / {counts[priority]} findings</h2>'
        for row in [x for x in issues if x['priority'] == priority]:
            register += f'<article class="issue" id="{row["id"]}"><span class="badge {priority.lower()}">{priority}</span> <span class="muted">{e(row["scope"])} / {e(row["area"])}</span><h3>{e(row["title"])}</h3><p class="muted"><code>{row["id"]}</code></p><p><strong>Observed:</strong> {e(row["observed"])}</p><p><strong>Impact:</strong> {e(row["why"])}</p><p><strong>Normal trigger:</strong> {e(row["normal_workflow"])}</p><p><strong>Minimal fix:</strong> {e(row["minimal_fix"])}</p>'
            if row['candidates']:
                register += '<p><strong>Suggested fix branch:</strong></p><ul class="branch-list">'
                for c in row['candidates']:
                    register += f'<li>{e(c["repository"])}: <code>{e(c["branch"])}</code> (<code>{c["head"][:10]}</code>), {e(size(c))}'
                    if c['id'] in {x['id'] for x in read(BASE_REPO / 'docs/local-testing/minimal-prs/catalog.json')['candidates']}:
                        register += ' / ' + a('review body and patch', '../development/prs/' + c['body'].replace('.md', '.html'))
                    register += '</li>'
                    if c['dependencies']:
                        register += '<li>Prerequisite: ' + ', '.join(a(fid, '#' + ('KLEBORATE-UPLOAD-422' if fid == 'KLEBORATE-CLIENT-COMPANION' else fid)) for fid in c['dependencies']) + '</li>'
                    if c['paired_candidates']:
                        register += '<li>Pair with: ' + e(', '.join(c['paired_candidates'])) + '</li>'
                    if c.get('policy_condition'):
                        register += '<li>Conditional mitigation: ' + e(c['policy_condition']) + '</li>'
                register += '</ul>'
            else:
                register += '<p><strong>Suggested fix branch:</strong> None prepared. The fix scope above is an estimate; no branch name or completed patch is implied.</p>'
            if row.get('caveat'):
                register += f'<p><strong>Review limit:</strong> {e(row["caveat"])}</p>'
            register += f'<p><strong>Verification:</strong> {e(row["validation"])}</p><details><summary>Acceptance criteria and evidence</summary><p>{e(row["acceptance"])}</p><p>{e(row["basis"])}</p><p>' + ' / '.join(a('Evidence ' + str(i + 1), target) for i, target in enumerate(row['evidence'])) + '</p></details></article>'
    register += '</section>'
    branches = '<section id="branches"><h2>Verified local fix branches</h2><p>44 local branch heads and production diffs were checked. No branch was pushed. Complete repository paths, full commits, bases, dependencies and file sizes are in <a href="data/branches.json">the branch register</a>; <a href="data/issues.csv">the CSV</a> maps every finding to its candidate or open status.</p>'
    for repository in ['Bonsai', 'SDK', 'PRP', 'JASEN']:
        rows = [c for c in candidates if c['repository'] == repository]
        branches += f'<h3>{repository}: {len(rows)} branches</h3><ul class="branch-list">'
        branches += ''.join(f'<li><code>{e(c["branch"])}</code> / <code>{c["head"][:10]}</code> / {e(size(c))}</li>' for c in rows)
        branches += '</ul>'
    branches += '<p class="muted">The SDK repository is nested under Bonsai; PRP is separate. The JASEN branch is in the external producer checkout. The private-record branch disables new private-marked creation; it does not add ACLs or repair existing records. Dependencies and merge overlap notes remain part of the review.</p></section>'
    screenshots = '<section id="screenshots"><h2>Selected screenshot evidence</h2><p>Original development evidence and later patched-instance evidence are labelled separately. Full-resolution PNGs are linked for inspection.</p>'
    for row in content['screenshots']:
        screenshots += f'<figure><h3>{e(row["title"])}</h3><a href="assets/{e(row["name"])}"><img loading="lazy" src="assets/{e(row["name"])}" alt="{e(row["title"], quote=True)}"></a><figcaption>{e(row["caption"])} {a(row["issue"], "#" + row["issue"])}</figcaption></figure>'
    screenshots += '</section>'
    species = '<section id="species"><h2>Species context</h2><p>Clinical orientation to the profile names; this is separate from software coverage and diagnostic validation.</p>'
    for row in content['species_context']:
        species += f'<h3>{e(row["profile"])}</h3><p>{e(row["context"])} {a("Clinical source", row["source"])}'
        if row.get('source2'):
            species += ' / ' + a('Additional source', row['source2'])
        species += '</p>'
    species += '</section>'
    handoff = '<section id="handoff"><h2>Handoff and remaining limits</h2>' + paras(content['handoff'])
    handoff += '<details><summary>Full coverage limits</summary>' + paras(content['limits']) + '</details><p><a href="technical.html">Methods, source context and preservation</a> / <a href="figures.html">Figure index</a> / <a href="data/issues.json">Machine-readable findings</a></p></section>'
    body = header + order + coverage + register + branches + screenshots + species + handoff
    body = re.sub(r'(<img class="chart" src="assets/(priorities|regression)\.svg"[^>]*>)',
        lambda match: '<picture><source media="(max-width:600px)" srcset="assets/' +
        match[2] + '-mobile.svg">' + match[1] + '</picture>', body)
    (OUTPUT / 'index.html').write_text(shell(content['title'], body))
    technical = '<header><p class="eyebrow">FINAL REVIEW / TECHNICAL NOTE</p><h1>Attribution, reproducibility and limits</h1><p><a href="index.html">Return to final report</a></p></header><section><h2>Question, status and scope</h2>'
    technical += paras([content['question'], content['status'], content['scope'], content['counting_rule']])
    technical += '<h2>Pinned sources</h2><p>Bonsai development <code>' + context['development_commit'] + '</code>; SDK baseline <code>' + context['sdk_baseline'] + '</code>. PRP baseline <code>' + context['prp_baseline'] + '</code>; JASEN <code>' + context['jasen_baseline'] + '</code>.</p><p>The final offline audit uses SDK <code>' + context['parser_audit']['sdk']['head'] + '</code> and PRP <code>' + context['parser_audit']['prp']['head'] + '</code>. These include local fixes. See <a href="data/source-context.json">full source context</a> and <a href="data/branches.json">verified branch refs</a>.</p>'
    technical += '<h2>Baseline evidence strength</h2><ul>' + ''.join(f'<li>{e(k)}: {v} findings</li>' for k, v in context['baseline_evidence_counts'].items()) + '</ul><p>The original source audit remains available in the preserved development report. Later findings are labelled by their actual tested repository/revision rather than silently attributed to the unpatched application.</p>'
    technical += '<h2>Rebuild</h2><p>Authored content: <code>docs/local-testing/final-review-content.json</code>. Generator: <code>scripts/build_final_report.py</code>. The report source is on <code>' + e(context['report_source_branch']) + '</code>.</p><p><code>PYTHONPATH=/home/jakob/data/codex/bonsai/environments/final-report-deps python3 scripts/build_final_report.py</code></p><p>The generator reads existing saved evidence, verifies local Git refs and production diffs, and writes only the new final-report directory plus operational QA files on the external data drive. It does not run JASEN, upload analyses, change application code, mutate the database, push branches or overwrite earlier reports.</p>'
    technical += '<h2>Limits</h2>' + paras(content['limits'])
    technical += '<h2>Preservation and verification</h2><p>Earlier report files and screenshots are hash-checked before and after generation. Public snapshots are curated; credentials, raw logs, browser DOM and biological payloads are not copied into the report. <a href="data/preservation.json">Preservation receipt</a> / <a href="data/provenance.json">Input and output hashes</a> / <a href="data/report-qa.json">Delivery QA</a>.</p></section>'
    (OUTPUT / 'technical.html').write_text(shell('Bonsai final report - technical note', technical))
    (OUTPUT / 'figures.html').write_text(shell('Bonsai final report - figure index', '<header><h1>Figure index</h1><p><a href="index.html">Final report</a></p></header><section><h2>Reading tasks</h2><p><a href="index.html#review-order">Release urgency and candidate availability: Figure 1</a></p><p><a href="index.html#coverage">Final patched parser regression: Figure 2</a></p><p><a href="index.html#screenshots">Observed UI failures: four original screenshots</a></p><p><a href="data/issues.json">Exact issue data</a> / <a href="data/parser-audit-results.json">Exact regression data</a></p></section>'))


def main():
    old = preserved_reports()
    content = read(CONTENT)
    issues, candidates, verified, counts, context, original_catalog = assemble(content)
    for path in [OUTPUT / 'assets', OUTPUT / 'data', RUN]:
        path.mkdir(parents=True, exist_ok=True)
    source_paths = [CONTENT, Path(__file__), REPO / 'scripts/check_final_report.py',
        SITE / 'development/data/development-findings.json',
        BASE_REPO / 'docs/local-testing/minimal-prs/catalog.json',
        PILOT / 'pipeline-status.json', PILOT / 'bonsai/index-auth-fix.json',
        PILOT / 'bonsai/read-pair-count-fix.json', HUB / 'docs/data/loaded-results.json',
        HUB / 'cases/klebsiella/saved-report-ingestion/local-fixes.json', AUDIT / 'result.json']
    for row in content['screenshots']:
        src = SITE / row['source']
        shutil.copy2(src, OUTPUT / 'assets' / row['name'])
        source_paths.append(src)
    ledger = {'as_of': content['as_of'], 'scope': content['scope'], 'counting_rule': content['counting_rule'],
        'issue_count': len(issues), 'counts_by_priority': counts, 'product_findings': 63,
        'fixture_only_findings': 1, 'prepared_branches': 44, 'findings_with_candidates': 43,
        'findings_without_candidates': 21, 'findings': issues}
    write_json(OUTPUT / 'data/issues.json', ledger)
    write_json(OUTPUT / 'data/branches.json', {'scope': 'Local review candidates, not published PRs',
        'verified_at_utc': datetime.now(timezone.utc).isoformat(), 'branch_count': len(candidates),
        'branches': candidates, 'ref_checks': verified, 'original_integration_checks': original_catalog['integration']})
    write_json(OUTPUT / 'data/source-context.json', context)
    audit = read(AUDIT / 'result.json')
    write_json(OUTPUT / 'data/parser-audit-results.json', audit)
    write_json(OUTPUT / 'data/native-control-checks.json', {
        'scope': 'Existing completed laboratory control; no new producer work',
        'browser': read(PILOT / 'bonsai/browser-status.json'),
        'fidelity': read(PILOT / 'bonsai/fidelity-status.json'),
        'authorization_retest': read(PILOT / 'bonsai/index-auth-live-retest.json')})
    producer = read(PILOT / 'pipeline-status.json')
    write_json(OUTPUT / 'data/native-control-provenance.json', {
        'scope': 'Existing completed K-12 laboratory-control software integration, not clinical validation',
        'status': producer['status'], 'upstream_commit': producer['upstream_commit'],
        'upstream_version': producer['upstream_version'],
        'local_producer_patch': producer['local_producer_patch'],
        'manifest_sha256': producer['manifest_sha256'],
        'source_status_path': str(PILOT / 'pipeline-status.json')})
    write_json(OUTPUT / 'data/report-qa.json', {'status': 'PENDING',
        'instruction': 'Run scripts/check_final_report.py and inspect the final PDF renders before delivery'})
    with (OUTPUT / 'data/issues.csv').open('w', newline='') as stream:
        w = csv.writer(stream)
        w.writerow(['priority', 'issue', 'title', 'scope', 'normal_trigger', 'minimal_fix',
            'suggested_fix_branches', 'production_changes', 'status'])
        for row in issues:
            w.writerow([row['priority'], row['id'], row['title'], row['scope'], row['normal_workflow'],
                row['minimal_fix'], branch_text(row), '; '.join(size(c) for c in row['candidates']),
                'Candidate prepared; not merged' if row['candidates'] else 'No separate candidate prepared'])
    s = styles()
    drawings = [priority_figure(issues), regression_figure(audit)]
    all_drawings = drawings + list(mobile_figures(issues))
    for name, drawing in zip(['priorities.svg', 'regression.svg',
                             'priorities-mobile.svg', 'regression-mobile.svg'], all_drawings):
        path = OUTPUT / 'assets' / name
        renderSVG.drawToFile(drawing, str(path))
        svg = re.sub(r'<!DOCTYPE.*?>', '', path.read_text(), flags=re.S)
        path.write_text(svg)
    loaded = read(HUB / 'docs/data/loaded-results.json')
    render_html(content, issues, candidates, counts, loaded, context)
    pdf = pdf_report(content, issues, candidates, counts, drawings, loaded, context, s)
    after = preserved_reports()
    if old != after:
        raise ValueError('An earlier report changed during generation')
    preservation = {'verified_at_utc': datetime.now(timezone.utc).isoformat(),
        'earlier_files_checked': len(old), 'all_unchanged': True,
        'files': old, 'scope': 'Earlier served reports, evidence and PDF files; final/ excluded'}
    write_json(OUTPUT / 'data/preservation.json', preservation)
    provenance = {'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'inputs': {str(p): digest(p) for p in source_paths},
        'outputs': {str(p.relative_to(OUTPUT)): digest(p) for p in OUTPUT.rglob('*')
            if p.is_file() and p.name not in {'provenance.json', 'report-qa.json'}},
        'generator': str(Path(__file__)), 'report_source_branch': context['report_source_branch'],
        'report_source_parent': context['report_source_parent'], 'new_sequence_analyses': 0,
        'application_database_mutations': 0, 'git_pushes': 0}
    write_json(OUTPUT / 'data/provenance.json', provenance)
    write_json(RUN / 'build-result.json', {'html': str(OUTPUT / 'index.html'), 'pdf': str(pdf),
        'findings': len(issues), 'priorities': counts, 'branches': len(candidates),
        'old_files_unchanged': len(old)})
    print(json.dumps({'html': str(OUTPUT / 'index.html'), 'pdf': str(pdf),
        'findings': len(issues), 'priorities': counts, 'branches': len(candidates),
        'earlier_files_unchanged': len(old)}))


if __name__ == '__main__':
    main()
