"""Render the separate bounded increment without changing earlier evidence."""

from collections import Counter
from html import escape
import json
from pathlib import Path

from build_species_findings import REPO, render_chart


def render(run, output, publish, figure):
    root = run / "bounded/2026-11-07"
    if not (root / "results.jsonl").exists():
        return "", ""
    latest = {}
    for line in (root / "results.jsonl").read_text().splitlines():
        item = json.loads(line)
        latest[(item["phase"], item["surface"], item["role"], item["case"], item.get("sample"))] = item
    cases = list(latest.values())
    counts = {}
    for item in cases:
        counts.setdefault(item["phase"] + "/" + item["surface"], Counter())[item["status"]] += 1
    (root / "results-latest.json").write_text(json.dumps({"counts": counts, "cases": cases}, indent=2) + "\n")
    results_url = publish("bounded/2026-11-07/results-latest.json")
    scope_url = publish("bounded/2026-11-07/scope.json")
    second_scope_url = publish("bounded/2026-11-07/scope-stored-read.json") if (root / "scope-stored-read.json").exists() else scope_url
    context_url = publish("bounded/2026-11-07/context.json")
    regression_url = publish("bounded/2026-11-07/regressions.json") if (root / "regressions.json").exists() else None
    support_url = publish("bounded/2026-11-07/support-context.json") if (root / "support-context.json").exists() else None
    findings = json.loads((root / "findings.json").read_text()) if (root / "findings.json").exists() else []
    content_path = REPO / "docs/local-testing/bounded-findings-content.json"
    content = json.loads(content_path.read_text())
    pieces = ['<section class="section" id="bounded"><div class="section-heading"><h2>Bounded follow-up: incremental software checks</h2></div><div class="scope">',
        '<p>Each increment has fixed actions and exclusions. Application failures and platform limitations are tracked separately. Successful execution does not establish permission for broader biological work.</p>',
        f'<p><a href="{scope_url}">First-increment scope</a> · <a href="{second_scope_url}">Stored-report increment scope</a> · <a href="{context_url}">Run context</a> · <a href="{results_url}">Exact observations</a></p>',
        '<p>Compute workers were stopped during the checks and restored afterward. Pipeline execution, raw sequencing work, analysis/clustering jobs and curation writes are excluded. Record deletion queued ordinary index-cleanup work while workers were stopped.</p>']
    if regression_url:
        pieces.append(f'<p><a href="{regression_url}">49 passing regression and scope-guard checks</a>. Both increments completed without a new platform safety notice being observed. This is an observation about these tasks, not permission for wider biological work.</p>')
    context = json.loads((root / "context.json").read_text())
    if context.get("application_patch_commit"):
        pieces.append(f'<p>Bounded application patch: <code>{escape(context["application_patch_commit"])}</code>. Stored results and decisions were preserved. The 80-summary sweep checked availability and record identity, not scientific correctness.</p>')
    if (root / "end-state.json").exists():
        end_url = publish("bounded/2026-11-07/end-state.json")
        pieces.append(f'<p>The seven disposable records and their temporary groups were removed. The original 125 records, 12 groups and four accounts remain. <a href="{end_url}">Cleanup verification</a>.</p>')
    if support_url:
        pieces.append(f'<details class="technical"><summary>Scope setup and the earlier safety notice</summary><div class="details-body"><p>Run <code>bash scripts/bounded-test.sh scope</code> to print the working boundary; <code>bash scripts/bounded-test.sh guards</code> checks the route guards. These are local operational controls, not platform approval.</p><p>Detailed findings may be available from a review action on the original notice in a supported desktop/web client. The earlier biological-risk error had no detailed findings attached locally. If no action is offered, the <a href="{support_url}">small support-context file</a> contains its timestamp, identifiers and visible error for an inquiry to Support. Nothing is sent automatically.</p></div></details>')
    for label, outcomes in counts.items():
        asset = "assets/" + label.replace("/", "-") + ".svg"
        render_chart(outcomes, output / asset)
        words = ', '.join(f'{n} {status.lower()}' for status, n in outcomes.items())
        pieces.append(f'<figure><h3>{escape(label.replace("/", " · "))}</h3><img src="{asset}" width="850" height="55" alt="{escape(words)}"><figcaption>{escape(words)}; denominator {sum(outcomes.values())} recorded checks in this phase and surface. <a href="{results_url}">Exact data</a>. Counts do not measure total product coverage.</figcaption></figure>')
    pieces.append('</div>')
    for finding in findings:
        authored = content[finding["id"]]
        pieces.append(f'<article class="finding" id="{finding["id"]}"><div class="finding-head"><span class="badge">{escape(authored["severity"])} · {escape(finding["status"])}</span><h3>{escape(authored["title"])}</h3></div><div class="finding-body"><p>{escape(authored["impact"])}</p><p>{escape(finding["summary"])}</p>')
        shots = finding.get("screenshots", [])
        if shots:
            pieces.append('<div class="gallery' + (' single' if len(shots) == 1 else '') + '">')
        for shot in shots:
            pieces.append(figure(shot))
        if shots:
            pieces.append('</div>')
        pieces.append(f'<p class="retest"><strong>Retest</strong>{escape(authored["retest"])}</p></div></article>')
    pieces.append('</section>')
    publish("bounded/2026-11-07/findings.json")
    total = sum(sum(c.values()) for c in counts.values())
    critical_verified = sum(content[f["id"]]["severity"] == "Proposed blocker" and f["status"].startswith("verified") for f in findings)
    summary = (f'Two bounded software increments have {total} recorded observations across baselines and retests. '
               f'{critical_verified} additional blockers passed targeted fix retests; record-level private visibility remains an open scope gap. ')
    return ''.join(pieces), summary
