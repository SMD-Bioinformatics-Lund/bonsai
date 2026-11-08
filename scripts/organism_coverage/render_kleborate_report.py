#!/usr/bin/env python3
"""Render the requested saved-report integration findings and local fix evidence."""
import html
import json
import shutil

from kleborate_saved_report_cases import ROOT, HUB, REPO, now, write


def main():
    verification = json.loads((ROOT / 'verification-status.json').read_text())
    assert verification['status'] in {'COMPLETE', 'COMPLETE_WITH_FINDINGS'}
    imports = json.loads((ROOT / 'import-status.json').read_text())
    fixes = json.loads((ROOT / 'local-fixes.json').read_text())
    baseline = json.loads((ROOT / 'baseline-result.json').read_text())
    checks = verification['checks']; passed = sum(c['status'] == 'PASS' for c in checks)
    fidelity = [c for c in checks if c['name'] == 'parser-to-stored-envelopes']
    evidence = {'generated_at_utc': now(), 'imports': imports, 'verification': verification,
        'local_fixes': fixes, 'baseline': baseline, 'scope': 'One saved report pair reused for four software scenarios, not four biological samples'}
    public = HUB / 'docs/kleborate'; (public / 'data').mkdir(parents=True, exist_ok=True)
    write(public / 'data/evidence.json', evidence)
    shutil.copy2(REPO / 'datasets/bonsai_kleborate_saved_report_cases.json', public / 'data/provenance.json')
    e = html.escape
    bars = [('Saved-report imports', 4, 4), ('Parser-to-storage comparisons', sum(c['status'] == 'PASS' for c in fidelity), len(fidelity)),
        ('Functional checks', passed, len(checks)), ('Focused fix regression tests', 9, 9)]
    elements = []
    for i, (label, count, total) in enumerate(bars):
        y = i * 75
        elements.append(f'<text x="0" y="{y+18}" font-size="16">{e(label)}: {count}/{total}</text><rect y="{y+30}" width="480" height="20" fill="#ba4c3a"/><rect y="{y+30}" width="{480*count/max(1,total):.2f}" height="20" fill="#16836d"/>')
    (public / 'checks.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 290" role="img" aria-label="Four imports succeed; reading checks retain failures"><rect width="480" height="290" fill="white"/><g font-family="sans-serif" fill="#172b3d">'+''.join(elements)+'</g></svg>')
    findings = [
        ('P1', 'Open', 'Kleborate summary dispatch loses or misrepresents stored results',
         'The species card omits its stored label; K/O labels are missing or use the wrong card; the supplied-result AMR card is blank. A score-only object is presented as an empty gene list.',
         'Reproduced under both assay names. The score and label failures also occur in the synthetic header-only companion controls.',
         'Limited frontend template work: add dispatch for the existing Kleborate result shapes and a K/O-specific reading card. Larger than the two import fixes; no storage or workflow restructuring is indicated.'),
        ('P1', 'Fixed locally', 'PRP does not forward the listed companion file',
         'The pinned uploader fails with HTTP 422 after creating the sample. No partial analysis descriptors are stored. The local branch attaches the companion to Kleborate and skips it as a standalone upload.',
         'Normal manifests that list Kleborate and hAMRonization separately; feature-dependent local usage frequency remains unmeasured.',
         '13 additions and 1 deletion in one production file; 5 focused tests pass. Requires the existing paired API/SDK companion support.'),
        ('P1', 'Fixed locally', 'Kaptive fields are read from the wrong block and percentage notation is rejected',
         'The original saved report is rejected by the API. The local SDK branch reads the nested block and converts explicit percentage notation to the model’s fraction representation.',
         'Reports with the saved Kleborate 3.2.4 field structure; this fixture triggered whole-upload rejection.',
         '5 additions and 3 deletions in one production parser file; 4 focused tests pass. No report values were edited.'),
    ]
    finding_rows = ''.join('<tr>'+''.join(f'<td>{e(v)}</td>' for v in row)+'</tr>' for row in findings)
    case_rows = []
    for case in imports['cases']:
        related = [c for c in checks if c['case'] == case['key']]
        ok = sum(c['status'] == 'PASS' for c in related)
        case_rows.append(f'<tr><th><a href="http://100.90.51.21:18100/sample/{e(case["sample_id"])}">{e(case["key"])}</a></th><td>1</td><td>{case["view_descriptors"]}</td><td>{e(case["descriptor_statuses"]["amr"])}</td><td>{ok}/{len(related)}</td></tr>')
    figures = []
    for item in verification['screenshots']:
        source = ROOT / item['path']
        if source.name not in {'klebsiella-provided-summary.png', 'klebsiella-header-only-summary.png', 'kpneumoniae-provided-summary.png'}: continue
        destination = public / 'evidence' / source.name; destination.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, destination)
        figures.append(f'<figure><img src="evidence/{e(source.name)}" alt="Saved-report summary showing the unresolved reading gaps"><figcaption>{e(source.stem)}: the summary opens, while stored labels and supported result content are missing or misrepresented. This is software-display evidence, without biological interpretation. <a href="data/evidence.json">Exact checks and source screenshot hashes</a>.</figcaption></figure>')
    branch_rows = ''.join(f'<tr><th>{e(name)}</th><td><code>{e(fixes[name]["branch"])}</code></td><td><code>{e(fixes[name]["head"])}</code></td></tr>' for name in ['PRP', 'SDK'])
    failed_rows = ''.join(f'<tr><td>{e(c["case"])}</td><td>{e(c["name"])}</td></tr>' for c in checks if c['status'] == 'FAIL')
    page = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bonsai — saved Kleborate integration</title><style>body{{font:16px/1.55 system-ui,sans-serif;color:#172b3d;background:#f4f7fa;margin:0}}main{{max-width:1080px;margin:auto;padding:24px}}section,header{{padding:22px;background:white;margin-bottom:20px;border-radius:10px}}h1{{font-size:28px;line-height:1.2}}h2{{font-size:21px}}a{{color:#056c83}}.notice{{border-left:5px solid #bd6532;padding-left:14px}}.table{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{padding:9px;text-align:left;vertical-align:top;border-bottom:1px solid #d8e1e9}}code{{overflow-wrap:anywhere}}figure{{margin:20px 0}}img{{max-width:100%;height:auto}}.chart{{width:480px}}figcaption,small{{font-size:13px;color:#455a6d}}@media(max-width:600px){{main{{padding:10px}}section,header{{padding:16px}}}}@media print{{body{{background:white}}main{{padding:0}}header,figure{{break-inside:avoid}}}}</style><main><header><p>BONSAI / SAVED-REPORT INTEGRATION</p><h1>Do saved Kleborate reports import and display correctly?</h1><p><strong>Import and storage pass with two minimal local fixes. Summary display remains incomplete.</strong> The focused test is prepared and has been executed through the ordinary viewing account. <strong>{passed}/{len(checks)} functional checks passed</strong>; the failed checks concern summary rendering.</p><p class="notice">Both assay names were exercised with the existing companion and a synthetic header-only companion. These are four software scenarios derived from one report pair, not four independent isolates. No new sequencing pipeline, biological prediction or interpretation was performed.</p><figure><img class="chart" src="checks.svg" alt="4/4 imports, {passed}/{len(checks)} functional checks, 9/9 focused fix tests passed"><figcaption>Green indicates passed checks and red indicates failures. Denominators: four software import scenarios, four whole-envelope storage comparisons, {len(checks)} functional checks and nine focused code regressions. The scenarios share one saved report pair; these counts do not measure clinical accuracy or biological diversity. <a href="data/evidence.json">Exact evidence</a>.</figcaption></figure><p><a href="../">Loaded-results overview</a> · <a href="../../development/">Development issue report</a> · <a href="data/provenance.json">Pinned source files and derivation</a></p><small>Snapshot: {e(evidence["generated_at_utc"])}. The application and SDK include the previously prepared local fixes. Nothing was pushed.</small></header><section><h2>Priorities and expected fix scope</h2><div class="table"><table><thead><tr><th>Priority</th><th>Status</th><th>Issue</th><th>Evidence</th><th>When triggered</th><th>Fix scope</th></tr></thead><tbody>{finding_rows}</tbody></table></div><p>Priorities reflect apparent user impact. Normal workflow frequency has not been measured. Automatic similarity-widget errors were also recorded for these deliberately unindexed records; comparison and clustering behavior were not evaluated.</p></section><section><h2>What is loaded?</h2><div class="table"><table><thead><tr><th>Software scenario</th><th>Analyses</th><th>Descriptors</th><th>Companion-derived descriptor status</th><th>Checks passed</th></tr></thead><tbody>{''.join(case_rows)}</tbody></table></div><p>Each record contains one Kleborate canonical analysis and its eleven result descriptors. hAMRonization is attached as a companion and is not uploaded as a second analysis. All parser values and statuses match the stored views after normalizing optional null-valued keys.</p><p>The header-only control is explicitly synthetic: its primary report is unchanged, so it is not a coherent biological no-findings sample. It checks an unavailable companion-derived result and must not be interpreted as a negative result. The mislabelled repository Quast report and original inconsistent run metadata were excluded.</p></section><section><h2>Local minimal branches</h2><div class="table"><table><thead><tr><th>Repository</th><th>Branch</th><th>Commit</th></tr></thead><tbody>{branch_rows}</tbody></table></div><p>The PRP candidate is based on 2.0.0; the SDK candidate is based on the SDK baseline used by the earlier reports. The isolated pilot uses the SDK fix composed with its existing local fixes. The import blockers are resolved locally; the P1 summary-reading issue remains open.</p><details><summary>Reproduction and failed checks</summary><p>Operational scripts: <code>scripts/organism_coverage/kleborate_saved_report_cases.py --baseline</code>, <code>activate_kleborate_fixes.py</code>, <code>kleborate_saved_report_cases.py</code>, then <code>check_kleborate_saved_reports.py</code>. Original failures, test logs, upload state and source heads are preserved outside Git. The captured baseline failure is preserved on repeated runs.</p><p>Before the PRP fix, three of five routing checks failed; after it, all five passed. Before the SDK fix, all four input-format checks failed; after it, all four passed.</p><div class="table"><table><thead><tr><th>Scenario</th><th>Failed functional check</th></tr></thead><tbody>{failed_rows}</tbody></table></div></details></section><section><h2>Screenshot evidence</h2>{''.join(figures)}</section></main></html>'''
    (public / 'index.html').write_text(page)
    print(f'Saved-report integration report rendered: {passed}/{len(checks)} functional checks passed; UI findings remain')


if __name__ == '__main__': main()
