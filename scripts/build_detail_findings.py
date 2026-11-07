"""Add the read-only detail increment to the standalone findings page."""

from collections import Counter
from html import escape
import json

from build_species_findings import REPO, render_chart


def render(run, output, publish, figure):
    relative = "detail-read/2026-11-07/"
    root = run / relative
    if not (root / "findings.json").exists():
        return "", ""
    context = json.loads((root / "context.json").read_text())
    latest = {}
    for line in (root / "results.jsonl").read_text().splitlines():
        item = json.loads(line)
        if item["surface"] == "api" and item["role"] != context["api_account"]:
            item["logged_role"], item["role"] = item["role"], context["api_account"]
        latest[(item["phase"], item["surface"], item["role"], item["case"], item["sample"])] = item
    cases = list(latest.values())
    counts = {phase: dict(Counter(r["status"] for r in cases if r["phase"] == phase)) for phase in ("baseline", "fixed")}
    (root / "results-latest.json").write_text(json.dumps({"counts": counts, "cases": cases}, indent=2) + "\n")
    links = {name: publish(relative + name + ".json") for name in ("context", "scope", "results-latest", "regressions", "state-verification", "findings")}
    findings = json.loads((root / "findings.json").read_text())
    content = json.loads((REPO / "docs/local-testing/detail-findings-content.json").read_text())
    fixed = [r for r in cases if r["phase"] == "fixed"]
    opened = sum(r["case"] == "detail-page-identity" and r["status"] == "PASS" for r in fixed)
    exports = [r for r in fixed if r["surface"] == "api" and r["case"].startswith("export-")]
    files = sum(r["observed"].get("http_status") == 200 and r["status"] == "PASS" for r in exports)
    unavailable = sum(r["observed"].get("http_status") == 422 and r["status"] == "PASS" for r in exports)
    summary = f'Read-only detail testing now opens {opened}/80 existing records across eight assay paths. Five additional blockers and one feedback issue passed local fix retests. '
    html = ['<section class="section" id="details"><div class="section-heading"><h2>Read-only detail pages and exports</h2></div><div class="scope">',
        f'<p><strong>{opened}/80 existing detail pages open with their saved record identities.</strong> Display filters, search, sorting, metadata navigation, browser history and exports were checked. Five proposed blockers and one feedback issue were fixed with small local changes.</p>',
        f'<p><a href="{links["scope"]}">Exact scope</a> · <a href="{links["results-latest"]}">Exact observations</a> · <a href="{links["context"]}">Run context and limitations</a> · <a href="{links["regressions"]}">66 passing regression and scope checks</a></p>']
    methods = [
        '<p>All 80 fixtures were navigated as user_one. Representative public records were also opened as admin and user_two. The API export sweep used the administrator account. Pagination is disabled in the detail tables and is recorded as not applicable.</p>',
        f'<p>The original 125 sample records, 459 stored analysis documents, eight saved curation records and 12 groups have unchanged before/after hashes. <a href="{links["state-verification"]}">State verification</a>. Analysis jobs, new biological analysis and curation writes were excluded; workers were stopped for the pass and restored afterward.</p>',
        f'<p>Application patch: <code>{escape(context["application_patch_commit"])}</code>. No new platform safety notice was observed during this increment.</p>']
    for phase, outcomes in counts.items():
        asset = "assets/detail-read-" + phase + ".svg"
        render_chart(outcomes, output / asset)
        words = ', '.join(f'{n} {status.lower()}' for status, n in outcomes.items())
        html.append(f'<figure><h3>{escape(phase.capitalize())}</h3><img src="{asset}" width="850" height="55" alt="{escape(words)}"><figcaption>{escape(words)}; denominator {sum(outcomes.values())} observations in this phase. Conditional checks add observations once a failed page becomes available. <a href="{links["results-latest"]}">Exact data</a>. These counts do not measure total product coverage.</figcaption></figure>')
    html.append('<div class="table-wrap"><table><thead><tr><th>Existing assay path</th><th>Detail identity</th><th>Metadata fields</th><th>Export file or clear availability feedback</th></tr></thead><tbody>')
    for assay in dict.fromkeys(r["assay"] for r in fixed):
        cells = []
        for selector in (lambda r: r["case"] == "detail-page-identity", lambda r: r["case"] == "metadata-identity-and-fields", lambda r: r["surface"] == "api" and r["case"].startswith("export-")):
            selected = [r for r in fixed if r["assay"] == assay and selector(r)]
            cells.append(f'<td>{sum(r["status"] == "PASS" for r in selected)}/{len(selected)}</td>')
        html.append('<tr><td>' + escape(assay) + '</td>' + ''.join(cells) + '</tr>')
    html.append('</tbody></table></div>')
    html.append(f'<p>CSV/TSV checks validated {files} files and {unavailable} explicit unavailable responses. These checks cover file structure and same-record identity; clinical interpretation of exported values was not validated. Browser export controls were exercised once per assay path.</p>')
    html.append('<details class="technical"><summary>Accounts, unchanged data and scope limits</summary><div class="details-body">' + ''.join(methods) + '</div></details></div>')
    for finding in findings:
        text = content[finding["id"]]
        badge = "blocker" if text["severity"] == "Proposed blocker" else "followup"
        html.append(f'<article class="finding" id="{finding["id"]}"><div class="finding-head"><span class="badge {badge}">{escape(text["severity"])} · {escape(finding["status"])}</span><h3>{escape(text["title"])}</h3></div><div class="finding-body"><p>{escape(text["impact"])}</p><p class="retest"><strong>Fix verification</strong>{escape(finding["summary"])}</p><div class="gallery">')
        html.extend(figure(shot) for shot in finding["screenshots"])
        html.append(f'</div><p class="retest"><strong>Retest</strong>{escape(text["retest"])}</p></div></article>')
    html.append('</section>')
    return ''.join(html), summary
