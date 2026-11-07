#!/usr/bin/env python3
"""Build the general-software expansion of the preserved local findings page."""

import argparse
from collections import Counter
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import re
import shutil
import struct
from urllib.parse import quote

from build_species_findings import DEFAULT_DATA, REPO, digest, many, read_json, render_chart

CONTENT = REPO / "docs/local-testing/general-findings-content.json"
TEMPLATE = REPO / "docs/local-testing/general-findings-page.html"
INITIAL_CASES = {
    "invalid-login", "normal-login-and-group-counts", "overview-search-by-external-id",
    "expired-session-navigation", "filtered-selection-and-basket", "basket-reload-persistence",
    "logout-confirmation", "basket-account-isolation", "basket-remove-one", "basket-clear",
    "admin-page-denied", "comment-create-escape", "qc-confirm-passed", "admin-user-list",
    "admin-password-minlength", "admin-password-policy-feedback", "admin-create-user",
    "admin-open-edit-user", "uploader-frontend-role", "admin-create-group",
    "admin-update-group-persistence", "admin-delete-empty-test-group",
}
EXCLUDED_EXPANDED = ("sample-detail-navigation", "variant-", "batch-variant-", "curation-", "tb-empty-", "cluster-")


def build(run, output):
    run, output = run.resolve(), output.resolve()
    if output == run or output.is_relative_to(REPO) or run.is_relative_to(output):
        raise ValueError("Choose a separate output directory on the project data drive")
    if not (output / "initial/index.html").is_file():
        raise ValueError("Preserve the delivered original page under output/initial first")
    context = read_json(run / "run-context.json")
    content = read_json(CONTENT)
    baseline = read_json(run / "findings.json") + read_json(run / "expanded-findings.json")
    findings = [x for x in baseline if x["id"] in content]
    if {x["id"] for x in findings} != set(content):
        raise ValueError("Every authored finding needs saved evidence")
    published, screenshots = {}, []

    def publish(relative):
        source = (run / relative).resolve()
        if not source.is_relative_to(run) or not source.is_file():
            raise ValueError(f"Missing or out-of-run evidence: {relative}")
        if source.suffix.lower() not in {".png", ".json", ".txt"}:
            raise ValueError(f"Do not publish browser DOM, logs or runtime files: {relative}")
        if source.suffix.lower() != ".png" and re.search(rb"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.", source.read_bytes()):
            raise ValueError(f"Token-shaped value in {relative}")
        target = output / "evidence" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        published[relative] = {"sha256": digest(source), "bytes": source.stat().st_size}
        return quote("evidence/" + relative, safe="/")

    def figure(item):
        url, caption = publish(item["path"]), escape(item["caption"])
        width, height = struct.unpack(">II", (run / item["path"]).read_bytes()[16:24])
        screenshots.append((url, item["caption"]))
        return (f'<figure class="screenshot"><button type="button" data-image="{url}" data-caption="{caption}" '
                f'aria-label="Enlarge screenshot: {caption}"><img src="{url}" width="{width}" height="{height}" '
                f'alt="{caption}" loading="lazy"><span class="zoom-hint">Enlarge ↗</span></button>'
                f'<figcaption>{caption} <a href="{url}" target="_blank" rel="noopener">Original PNG ↗</a></figcaption></figure>')

    fixes = read_json(run / "general-fix-verification.json") if (run / "general-fix-verification.json").exists() else {}
    account_closed = {"BASKET-ACCOUNT-SHARED": "ACCOUNT-BASKET-ISOLATION", "BASKET-UNDEFINED-ASSAY": "ACCOUNT-BASKET-HTML"} if (run / "account-sessions/2026-11-07/findings.json").exists() else {}
    recovery_ready = (run / "failure-recovery/2026-11-07/findings.json").exists()

    def card(finding):
        fid = finding["id"]
        text = content[fid]
        category = text["category"]
        label = {"blocker": "Proposed release blocker", "missing": "Missing metadata", "followup": "Follow-up"}[category]
        details = []
        for key in ("observed", "root_cause", "scope", "expected", "interpretation"):
            if finding.get(key):
                details.append(f'<h4>{escape(key.replace("_", " ").capitalize())}</h4><p>{escape(str(finding[key]))}</p>')
        links = []
        for relative in many(finding.get("evidence")):
            if Path(relative).suffix in {".json", ".png"}:
                links.append(f'<li><a href="{publish(relative)}">{escape(relative)}</a></li>')
        details.append('<h4>Saved baseline evidence</h4><ul>' + ''.join(links) + '</ul>')
        fix = fixes.get("findings", {}).get(fid)
        verification = ''
        if fid in account_closed:
            verification = f'<p class="retest"><strong>Resolved in the account/session iteration</strong><a href="#{account_closed[fid]}">Current fix verification and evidence</a>. The screenshots below preserve the earlier baseline.</p>'
        if fix:
            verification = '<p class="retest"><strong>Fix verification: ' + escape(fix["status"]) + '</strong>' + escape(fix["summary"]) + '</p>'
            for item in fix.get("screenshots", []):
                verification += figure(item)
            if fix.get("evidence"):
                verification += '<p class="footnote">Verification evidence: ' + ' · '.join(
                    f'<a href="{publish(path)}">{escape(Path(path).name)}</a>' for path in fix["evidence"]) + '</p>'
        if recovery_ready and fid == "COMMENT-HIDE-PERMISSION-500":
            verification = '<p class="retest"><strong>Resolved in the recovery iteration</strong>Ordinary accounts no longer see the administrator-only removal control. Denied direct requests show normal feedback. <a href="#RECOVERY-COMMENT-RETRY">Current verification and screenshots</a>. The images below preserve the earlier baseline.</p>'
        gallery = '<div class="gallery">' + ''.join(figure(x) for x in text["screenshots"]) + '</div>' if text["screenshots"] else ''
        return (f'<article class="finding" id="{fid}"><div class="finding-head"><div class="meta"><span class="badge {category}">{label}</span>'
                f'<a class="finding-id" href="#{fid}">{fid}</a></div><h3>{escape(text["title"])}</h3></div><div class="finding-body">'
                f'<p class="impact">{escape(text["impact"])}</p>{verification}{gallery}<p class="retest"><strong>Retest</strong>{escape(text["retest"])}</p>'
                '<details class="technical"><summary>Baseline reproduction and evidence</summary><div class="details-body">' + ''.join(details) + '</div></details></div></article>')

    cases = {}
    for phase, filename in (("initial", "ui-results.jsonl"), ("expanded-baseline", "expanded-ui-results.jsonl"), ("fixed", "general-fixed-ui-results.jsonl")):
        if not (run / filename).exists():
            continue
        for line in (run / filename).read_text().splitlines():
            item = json.loads(line)
            if phase == "initial" and item["case"] not in INITIAL_CASES:
                continue
            if phase == "expanded-baseline" and item["case"].startswith(EXCLUDED_EXPANDED):
                continue
            item["phase"] = phase
            cases[(phase, item["role"], item["case"], item.get("sample"))] = item
    counts = {phase: dict(Counter(x["status"] for x in cases.values() if x["phase"] == phase))
              for phase in dict.fromkeys(x["phase"] for x in cases.values())}
    (run / "general-ui-results-latest.json").write_text(json.dumps({"counts_by_phase": counts, "cases": list(cases.values())}, indent=2) + "\n")
    (run / "general-findings.json").write_text(json.dumps(findings, indent=2) + "\n")
    charts = []
    for phase, outcomes in counts.items():
        render_chart(outcomes, output / f"assets/general-{phase}.svg")
        summary = ', '.join(f'{value} {status.lower()}' for status, value in outcomes.items())
        charts.append(f'<figure><h3>{escape(phase.replace("-", " ").capitalize())}</h3><img src="assets/general-{phase}.svg" width="850" height="55" alt="{summary}"><figcaption>{summary}; total {sum(outcomes.values())} checks. <a href="evidence/general-ui-results-latest.json">Exact observations and denominators</a>.</figcaption></figure>')
    rendered = {f["id"]: card(f) for f in findings}
    from build_bounded_findings import render as render_bounded
    bounded_html, bounded_summary = render_bounded(run, output, publish, figure)
    from build_detail_findings import render as render_details
    detail_html, detail_summary = render_details(run, output, publish, figure)
    from build_account_findings import render as render_accounts
    account_html, account_summary = render_accounts(run, output, publish, figure)
    from build_recovery_findings import render as render_recovery
    recovery_html, recovery_summary = render_recovery(run, output, publish, figure)
    from build_parser_findings import render as render_parsers
    parser_html, parser_summary = render_parsers(run, output, publish, figure)
    categories = Counter(x["category"] for x in content.values())
    verified = {fid for fid, item in fixes.get("findings", {}).items() if item["status"] == "verified"}
    critical = {fid for fid, item in content.items() if item["category"] == "blocker"}
    critical_verified = len(critical & verified)
    opening = (f'<strong>{critical_verified} of {len(critical)} general-workflow blockers passed targeted fix verification.</strong> '
               f'{len(content) - len(verified)} smaller findings remain open. The unchanged baseline evidence and local fix results are kept separately below.') if fixes.get("findings") else (
               f'<strong>{len(critical)} proposed blockers affect ordinary application workflows.</strong> '
               'Group memberships, metadata, pending records, filtering and account administration require a release retest.')
    technical = ''
    if fixes.get("source_commit"):
        technical = (f'<h4>Local patch and verification</h4><p>Application patch: <code>{escape(fixes["source_commit"])}</code>. '
                     f'<a href="{publish("general-regression-results.json")}">Automated checks and commands</a> · '
                     f'<a href="{publish("general-fixed-api-results.json")}">Generic API probes</a>.</p>'
                     '<p>The production JavaScript build and TypeScript check passed. Branch source and compiled bundles were mounted into the recorded runtime images for this local test; shipped container images were not rebuilt.</p>'
                     '<p>Start the patched local stack with <code>bash scripts/general-test.sh up</code>. Rebuild its JavaScript with <code>bash scripts/general-test.sh build-js</code>. All generated assets remain on the external data drive.</p>')
    earlier_summary = fixes.get("summary", "Fix phase pending. All screenshots below describe the unchanged development candidate.")
    if account_html:
        earlier_summary = earlier_summary.replace("Six smaller findings remain open.", "The two basket follow-ups were resolved in the later account iteration.")
    replacements = {
        "BLOCKER_COUNT": str(categories["blocker"]), "OTHER_COUNT": str(len(content) - categories["blocker"]),
        "ANSWER": escape(parser_summary) if parser_html else escape(recovery_summary) if recovery_html else escape(account_summary) if account_html else (escape(detail_summary) + 'The record-level private visibility gap remains open. Earlier test phases and remaining smaller findings are preserved below.') if detail_html else escape(bounded_summary) + opening,
        "VERIFIED_COUNT": str(critical_verified), "BOUNDED": bounded_html, "DETAILS": detail_html, "ACCOUNTS": account_html, "RECOVERY": recovery_html, "PARSERS": parser_html,
        "FIX_SUMMARY": escape(earlier_summary),
        "FIX_BRANCH": escape(fixes.get("branch", "Pending creation after the expanded baseline")), "FIX_DETAILS": technical,
        "CHARTS": ''.join(charts),
        "BLOCKERS": ''.join(rendered[k] for k, v in content.items() if v["category"] == "blocker"),
        "OTHER": ''.join(rendered[k] for k, v in content.items() if v["category"] != "blocker"),
        "FINDINGS": publish("general-findings.json"), "UI_RESULTS": publish("general-ui-results-latest.json"),
        "APP_COMMIT": context["source_base_commit"], "SDK_COMMIT": context["sdk_revision"],
        "SCREENSHOT_INDEX": '<ul>' + ''.join(f'<li><a href="{url}">{escape(caption)}</a></li>' for url, caption in screenshots) + '</ul>',
        "RELEASE_REVIEW": ('<section class="overview"><h2>Current priorities and a condensed PDF</h2>'
                           '<p>The consolidated review supersedes historical open/fixed labels when prioritizing next week\'s work. '
                           'It identifies 15 open items, 41 locally fixed items and one explained case, with six access/workflow gates at the front of the queue.</p>'
                           '<div class="evidence-links"><a href="review/index.html">Read the prioritized review</a>'
                           '<a href="review/output/pdf/bonsai-release-review.pdf">Download the 8-page PDF</a>'
                           '<a href="review/technical.html">Methods and exact evidence</a></div></section>')
                          if (output / "review/index.html").is_file() else '',
    }
    if fixes:
        publish("general-fix-verification.json")
    html = re.sub(r"@@([A-Z_]+)@@", lambda m: replacements[m[1]], TEMPLATE.read_text())
    (output / "index.html").write_text(html)
    provenance = {"built_at": datetime.now(timezone.utc).isoformat(), "scope": "General application behavior and read-only stored summary/detail views; analysis execution and curation writes excluded",
                  "application_base_commit": context["source_base_commit"], "counts_by_phase": counts,
                  "finding_categories": dict(categories), "published_evidence": published,
                  "authoring_sources": {str(p.relative_to(REPO)): digest(p) for p in (
                      CONTENT, TEMPLATE, Path(__file__), REPO / "scripts/build_bounded_findings.py",
                      REPO / "docs/local-testing/bounded-findings-content.json", REPO / "docs/local-testing/bounded-scope.json",
                      REPO / "scripts/build_detail_findings.py", REPO / "docs/local-testing/detail-findings-content.json",
                      REPO / "scripts/build_account_findings.py", REPO / "docs/local-testing/account-findings-content.json",
                      REPO / "scripts/build_recovery_findings.py", REPO / "docs/local-testing/recovery-findings-content.json",
                      REPO / "scripts/build_parser_findings.py", REPO / "docs/local-testing/parser-findings-content.json")}}
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(json.dumps({"page": str(output / "index.html"), "findings": len(findings), "counts": counts, "screenshots": len(screenshots)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_DATA / "runs/species-ui-active")
    parser.add_argument("--output", type=Path, default=DEFAULT_DATA / "docs/development-findings")
    args = parser.parse_args()
    build(args.run_dir, args.output)
