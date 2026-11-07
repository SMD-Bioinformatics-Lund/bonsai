#!/usr/bin/env python3
"""Build a portable, illustrated reading page from the saved synthetic UI pass.

Only explicitly linked evidence is copied. Browser DOM, cookies, profiles and
other runtime files remain outside the published directory.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from html import escape
import json
from pathlib import Path
import re
import shutil
import struct
from urllib.parse import quote


REPO = Path(__file__).resolve().parents[1]
CONTENT = REPO / "docs/local-testing/findings-content.json"
TEMPLATE = REPO / "docs/local-testing/findings-page.html"
DEFAULT_DATA = Path.home() / "data/codex/bonsai"
LABELS = {"blocker": "Proposed release blocker", "missing": "Missing result",
          "question": "Scope decision needed", "followup": "Follow-up", "explained": "Explained"}


def many(value):
    return [] if value is None else value if isinstance(value, list) else [value]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_chart(counts, destination):
    """Reproduce an outcome plot from the deduplicated saved UI results."""
    total = sum(counts.values())
    segments = [("PASS", "Passed", "#387556"), ("FAIL", "Failed", "#b43c47"), ("N/A", "Not applicable", "#778994")]
    pieces = ['<svg xmlns="http://www.w3.org/2000/svg" width="850" height="55" viewBox="0 0 850 55" role="img" aria-labelledby="title desc">',
              '<title id="title">Recorded browser check outcomes</title>',
              f'<desc id="desc">{counts.get("PASS", 0)} passed, {counts.get("FAIL", 0)} failed, {counts.get("N/A", 0)} not applicable. Total {total} checks; not a count of distinct defects.</desc>']
    x = 0
    for status, _, color in segments:
        width = 850 * counts.get(status, 0) / total
        pieces.append(f'<rect x="{x:.3f}" y="14" width="{width:.3f}" height="32" fill="{color}"/>')
        x += width
    pieces.append('</svg>')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(pieces), encoding="utf-8")


def build(run, output):
    run, output = run.resolve(), output.resolve()
    if output == run or output.is_relative_to(REPO) or run.is_relative_to(output):
        raise ValueError("Choose a separate output directory on the project data drive")
    context = read_json(run / "run-context.json")
    findings = read_json(run / "findings.json")
    content = read_json(CONTENT)
    ui = read_json(run / "ui-results-latest.json")
    clustering = read_json(run / "species-clustering-results.json")
    if set(content) != {item["id"] for item in findings}:
        raise ValueError("Every saved finding must have an authored display entry")
    counts = dict(Counter(case["status"] for case in ui["cases"]))
    if counts != ui["counts"] or counts != context["ui_case_counts"]:
        raise ValueError("Saved UI counts disagree")
    # The opening summary describes this completed pass; reject stale hardcoded totals.
    if counts != {"PASS": 48, "FAIL": 13, "N/A": 1} or len(findings) != 13:
        raise ValueError("Update the authored snapshot summary for a different test pass")
    categories = Counter(item["category"] for item in content.values())
    if categories != {"blocker": 7, "missing": 1, "question": 2, "followup": 2, "explained": 1}:
        raise ValueError("Update the authored category totals")
    if len(clustering["results"]) != 28 or any(r["status"] != "PASS" for r in clustering["results"]):
        raise ValueError("Update the authored clustering summary")
    output.mkdir(parents=True, exist_ok=True)
    published = {}
    screenshots = []

    def publish(relative):
        relative = str(relative)
        source = (run / relative).resolve()
        if not source.is_relative_to(run) or not source.is_file():
            raise ValueError(f"Missing or out-of-run evidence: {relative}")
        if source.suffix.lower() not in {".png", ".json", ".log", ".nwk", ".txt"}:
            raise ValueError(f"Do not publish browser DOM or runtime files: {relative}")
        if source.suffix.lower() != ".png" and re.search(rb"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.", source.read_bytes()):
            raise ValueError(f"A token-shaped value must be removed before publishing: {relative}")
        target = output / "evidence" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        published[relative] = {"sha256": digest(source), "bytes": source.stat().st_size}
        return quote("evidence/" + relative, safe="/")

    def figure(item):
        url = publish(item["path"])
        raw = (run / item["path"]).read_bytes()
        width, height = struct.unpack(">II", raw[16:24])
        caption = escape(item["caption"])
        screenshots.append((url, item["caption"]))
        return (f'<figure class="screenshot"><button type="button" data-image="{url}" '
                f'data-caption="{caption}" aria-label="Enlarge screenshot: {caption}">'
                f'<img src="{url}" width="{width}" height="{height}" alt="{caption}" loading="lazy" decoding="async">'
                '<span class="zoom-hint" aria-hidden="true">Enlarge ↗</span></button>'
                f'<figcaption>{caption} <a href="{url}" target="_blank" rel="noopener">Original PNG ↗</a></figcaption></figure>')

    def gallery(items):
        if not items:
            return ""
        cls = "gallery single" if len(items) == 1 else "gallery"
        return f'<div class="{cls}">' + "".join(figure(item) for item in items) + '</div>'

    def card(finding, authored):
        category, fid = authored["category"], finding["id"]
        evidence = []
        for key in ("evidence", "diagnostic_evidence", "verification_evidence"):
            evidence.extend(many(finding.get(key)))
        links = []
        for relative in dict.fromkeys(evidence):
            url = publish(relative)
            links.append(f'<li><a href="{url}">{escape(relative)}</a></li>')
        technical = []
        for label, key in (("Affected scope", "scope"), ("Expected", "expected"), ("Observed", "observed"),
                           ("Cause identified", "root_cause"), ("Interpretation", "interpretation"), ("Verification", "verification")):
            if finding.get(key):
                technical.append(f'<h4>{label}</h4><p>{escape(finding[key])}</p>')
        if finding.get("steps"):
            technical.append('<h4>Reproduction steps from the pass</h4><ol>' + ''.join(f'<li>{escape(step)}</li>' for step in finding["steps"]) + '</ol>')
        if finding.get("source"):
            technical.append('<h4>Source locations</h4><ul>' + ''.join(f'<li><code>{escape(path)}</code></li>' for path in many(finding["source"])) + '</ul>')
        technical.append('<h4>Saved evidence</h4><ul>' + ''.join(links) + '</ul>')
        api = '<div class="api-evidence">HTTP 422 · Cannot parse AMR since no hAMRonization results were provided.</div>' if fid == "KLEBORATE-UPLOAD-422" else ""
        note = f'<p class="case-note">{escape(authored["note"])}</p>' if authored.get("note") else ""
        action_label = "Scope decision" if category == "question" else "Verification" if category == "explained" else "Retest after a fix"
        return (f'<article class="finding" id="{fid}"><div class="finding-head"><div class="meta">'
                f'<span class="badge {category}">{LABELS[category]}</span><a class="finding-id" href="#{fid}">{fid}</a></div>'
                f'<h3>{escape(authored["title"])}</h3></div><div class="finding-body"><p class="impact">{escape(authored["impact"])}</p>'
                + api + gallery(authored["screenshots"]) + note
                + f'<p class="retest"><strong>{action_label}</strong>{escape(authored["retest"])}</p>'
                + '<details class="technical"><summary>Reproduction and technical evidence</summary><div class="details-body">'
                + ''.join(technical) + '</div></details></div></article>')

    by_id = {item["id"]: item for item in findings}
    rendered = {fid: card(by_id[fid], item) for fid, item in content.items()}
    coverage = {}
    for result in clustering["results"]:
        coverage.setdefault(result["assay"], {})[result["method"]] = result["status"]
    table = '<table><caption class="small">API clustering coverage by assay path</caption><thead><tr><th scope="col">Assay</th><th scope="col">MinHash</th><th scope="col">SNV</th><th scope="col">MLST</th><th scope="col">cgMLST</th></tr></thead><tbody>'
    for assay, methods in coverage.items():
        table += f'<tr><th scope="row">{escape(assay)}</th>'
        for method in ("minhash", "ska", "mlst", "cgmlst"):
            table += '<td class="pass">Pass</td>' if methods.get(method) == "PASS" else '<td class="na">n/a</td>'
        table += '</tr>'
    table += '</tbody></table>'
    passing_gallery = gallery([
        {"path": "browser-results/user_one/full-access/minhash-tree-names.png", "caption": "Passing MinHash browser case: all nine selected sample names are represented, including samples grouped at identical distances. The downloaded Newick IDs were checked exactly."},
        {"path": "browser-results/user_one/full-access/tb001-igv-zoomed.png", "caption": "Passing IGV case: the 100 kb synthetic reference, BED annotation, coverage and overlapping reads are displayed at positions 1800–2300. IGV was opened directly because the sample summary was blocked."}
    ])
    replacements = {
        "BLOCKERS": ''.join(rendered[fid] for fid, item in content.items() if item["category"] == "blocker"),
        "OTHER": ''.join(rendered[fid] for fid, item in content.items() if item["category"] in {"missing", "question", "followup"}),
        "EXPLAINED": ''.join(rendered[fid] for fid, item in content.items() if item["category"] == "explained"),
        "COVERAGE_TABLE": table, "PASSING_GALLERY": passing_gallery,
        "FINDINGS": publish("findings.json"), "UI_RESULTS": publish("ui-results-latest.json"),
        "CLUSTER_RESULTS": publish("species-clustering-results.json"), "RUN_CONTEXT": publish("run-context.json"),
        "END_STATE": publish("end-state.json"), "APP_COMMIT": escape(context["source_base_commit"]),
        "SDK_COMMIT": escape(context["sdk_revision"]), "BRANCH": escape(context["branch"]),
        "HARNESS_COMMIT": escape(context["test_harness_commit"]),
        "SCREENSHOT_INDEX": '<ul>' + ''.join(f'<li><a href="{url}">{escape(caption)}</a></li>' for url, caption in screenshots) + '</ul>',
    }
    html = TEMPLATE.read_text(encoding="utf-8")
    html = re.sub(r"@@([A-Z_]+)@@", lambda match: replacements[match[1]], html)
    render_chart(counts, output / "assets/browser-checks.svg")
    (output / "index.html").write_text(html, encoding="utf-8")
    provenance = {"built_at": datetime.now(timezone.utc).isoformat(), "test_completed_at": context["last_updated"],
                  "source_run": str(run), "application_base_commit": context["source_base_commit"],
                  "ui_case_counts": counts, "finding_categories": dict(categories),
                  "authoring_sources": {str(path.relative_to(REPO)): digest(path) for path in (CONTENT, TEMPLATE, Path(__file__))},
                  "published_evidence": published, "screenshot_count": len(screenshots),
                  "notes": ["Screenshots are copied without alteration.", "Browser DOM, profiles, cookies and runtime directories are not published."]}
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"page": str(output / "index.html"), "findings": len(findings), "screenshots": len(screenshots), "evidence_files": len(published)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_DATA / "runs/species-ui-active")
    parser.add_argument("--output", type=Path, default=DEFAULT_DATA / "docs/development-findings")
    args = parser.parse_args()
    build(args.run_dir, args.output)


if __name__ == "__main__":
    main()
