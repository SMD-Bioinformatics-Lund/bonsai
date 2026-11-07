#!/usr/bin/env python3
"""Build a deduplicated, urgency-ranked HTML/PDF review from saved test evidence.

ReportLab is needed for rendering. All generated outputs default to the external
project data drive. Only explicitly listed JSON and PNG evidence is published.
The original phase reports and raw operational artifacts are never rewritten.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess

from reportlab.graphics import renderSVG
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, KeepTogether, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)


REPO = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("BONSAI_TEST_DATA", Path.home() / "data/codex/bonsai"))
CONTENT = REPO / "docs/local-testing/release-review-content.json"
AUDIT = "release-review/2026-11-07"
PARSER = "parser-display/2026-11-07"
SOURCE_FILES = [
    "findings.json", "expanded-findings.json", "general-fix-verification.json",
    "bounded/2026-11-07/findings.json", "detail-read/2026-11-07/findings.json",
    "account-sessions/2026-11-07/findings.json",
    "failure-recovery/2026-11-07/findings.json", f"{PARSER}/findings.json",
]
EXTRA_EVIDENCE = [
    f"{AUDIT}/context.json", f"{AUDIT}/gap-audit.json",
    f"{AUDIT}/permission-gate.json", f"{AUDIT}/source-audit.json",
    f"{AUDIT}/state-verification.json", f"{PARSER}/coverage.json",
    f"{PARSER}/regressions.json",
]
INK = "#193740"
MUTED = "#536b73"
TEAL = "#23685f"
LINE = "#d8e2e2"
PRIORITY_COLORS = {"P0": "#a73145", "P1": "#b66220", "P2": "#366ba0", "P3": "#6e7c86"}
TOKEN = re.compile(rb"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.")


def read(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()
    if TOKEN.search(encoded):
        raise ValueError(f"Token-shaped data refused: {path}")
    path.write_bytes(encoded)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def git_at(path, *args):
    return subprocess.check_output(["git", "-C", str(path), *args], text=True).strip()


def consolidate(run, content):
    observations = {}
    titles = {}
    for path in (REPO / "docs/local-testing").glob("*-findings-content.json"):
        for fid, item in read(path).items():
            titles[fid] = item.get("title", fid)
    for relative in SOURCE_FILES:
        value = read(run / relative)
        entries = value["findings"] if isinstance(value, dict) else value
        if isinstance(entries, dict):
            entries = [{"id": fid, **item} for fid, item in entries.items()]
        for item in entries:
            observations.setdefault(item["id"], []).append({**item, "source_document": relative})
    aliases = {alias: canonical for canonical, values in content["aliases"].items() for alias in values}
    if not set(aliases) <= set(observations):
        raise ValueError("An alias has no historical evidence")
    grouped = {}
    for fid, rows in observations.items():
        canonical = aliases.get(fid, fid)
        grouped.setdefault(canonical, []).extend(rows)
    # This permission/UI issue was closed as part of the broader retry fix.
    grouped["COMMENT-HIDE-PERMISSION-500"].append(observations["RECOVERY-COMMENT-RETRY"][-1])
    open_items = {item["id"]: item for item in content["open_findings"]}
    new_fixed = {item["id"]: item for item in content["new_fixed"]}
    ledger = []
    for fid in sorted(set(grouped) | set(open_items) | set(new_fixed)):
        rows = grouped.get(fid, [])
        source_ids = sorted({fid, *(item["id"] for item in rows if item["id"] != "RECOVERY-COMMENT-RETRY" or fid == "RECOVERY-COMMENT-RETRY")})
        entry = {"id": fid, "source_ids": source_ids, "historical_observations": rows}
        if fid in open_items:
            entry.update(open_items[fid])
            entry["status"] = "open"
            entry["partially_fixed"] = fid == "ECOLI-VARIANTS-EMPTY"
        elif fid in new_fixed:
            entry.update(new_fixed[fid])
            entry["status"] = "fixed_locally"
            entry["evidence_level"] = "Live read-only browser retest and 62 passing frontend tests"
        elif fid == "MINHASH-CLUSTER-FAIL":
            entry.update(status="explained", priority=None,
                         title="Failed-QC record was ineligible for the original clustering test",
                         summary=rows[-1]["interpretation"],
                         evidence_level="Historical baseline investigation; 28 eligible combinations passed")
        else:
            verified = [item for item in rows if item.get("status", "").startswith("verif")]
            if not verified:
                raise ValueError(f"No saved fix verification for {fid}")
            latest = verified[-1]
            title = next((titles[item["id"]] for item in reversed(rows) if item["id"] in titles), fid)
            entry.update(status="fixed_locally", priority=None, title=title,
                         summary=latest.get("summary", latest.get("observed", "Verified locally")),
                         evidence_level="Saved targeted fix verification", verification_source=latest["source_document"])
            entry["title"] = content.get("fixed_titles", {}).get(fid, entry["title"])
            if fid == "COMMENT-HIDE-PERMISSION-500":
                entry["summary"] = "Ordinary accounts no longer see Remove, and denied direct removal requests receive usable feedback. Administrator removal retains its existing audit behavior."
        entry["evidence"] = sorted(set(entry.get("evidence", [])) | {item["source_document"] for item in rows})
        ledger.append(entry)
    counts = Counter(item["status"] for item in ledger)
    priorities = Counter(item["priority"] for item in ledger if item["status"] == "open")
    if counts != {"open": 15, "fixed_locally": 41, "explained": 1}:
        raise ValueError(f"Review consolidation changed: {counts}")
    return {
        "as_of": content["as_of"], "historical_unique_ids": len(observations),
        "new_unique_ids": len((set(open_items) | set(new_fixed)) - set(observations)),
        "counts": dict(counts), "open_by_priority": dict(priorities),
        "counting_rule": "Related phase IDs are consolidated using the explicit alias map. Partial scope fixes remain open. The explained case is excluded from actionable counts; test observations are not defect counts.",
        "aliases": content["aliases"], "findings": ledger,
    }


def chart(ledger, mobile=False):
    if mobile:
        d = Drawing(280, 290)
        d.add(String(0, 274, "Open findings by urgency", fontName="ReviewBold", fontSize=13, fillColor=colors.HexColor(INK)))
        for i, priority in enumerate(("P0", "P1", "P2", "P3")):
            y = 238 - i * 33
            value = ledger["open_by_priority"].get(priority, 0)
            d.add(String(0, y + 2, priority, fontName="ReviewBold", fontSize=12, fillColor=colors.HexColor(INK)))
            d.add(Rect(32, y - 1, value * 26, 20, fillColor=colors.HexColor(PRIORITY_COLORS[priority]), strokeColor=None))
            d.add(String(40 + value * 26, y + 2, str(value), fontName="ReviewBold", fontSize=12, fillColor=colors.HexColor(INK)))
        d.add(String(0, 98, "Consolidated status", fontName="ReviewBold", fontSize=13, fillColor=colors.HexColor(INK)))
        for x, value, label, color in [(0, 41, "fixed locally", TEAL), (100, 15, "still open", PRIORITY_COLORS["P0"]), (193, 1, "explained", MUTED)]:
            d.add(String(x, 50, str(value), fontName="ReviewBold", fontSize=29, fillColor=colors.HexColor(color)))
            d.add(String(x, 26, label, fontName="Review", fontSize=11, fillColor=colors.HexColor(INK)))
        return d
    d = Drawing(480, 165)
    d.add(String(0, 151, "Open items by recommended urgency", fontName="ReviewBold", fontSize=10, fillColor=colors.HexColor(INK)))
    for i, priority in enumerate(("P0", "P1", "P2", "P3")):
        y = 119 - i * 29
        value = ledger["open_by_priority"].get(priority, 0)
        d.add(String(0, y + 2, priority, fontName="ReviewBold", fontSize=10, fillColor=colors.HexColor(INK)))
        d.add(Rect(30, y - 1, value * 23, 17, fillColor=colors.HexColor(PRIORITY_COLORS[priority]), strokeColor=None))
        d.add(String(36 + value * 23, y + 2, str(value), fontName="ReviewBold", fontSize=10, fillColor=colors.HexColor(INK)))
    d.add(String(290, 151, "Consolidated status", fontName="ReviewBold", fontSize=10, fillColor=colors.HexColor(INK)))
    for y, value, label, color in [(112, 41, "fixed locally", TEAL), (72, 15, "still open", PRIORITY_COLORS["P0"]), (32, 1, "explained case", MUTED)]:
        d.add(String(290, y, str(value), fontName="ReviewBold", fontSize=25, fillColor=colors.HexColor(color)))
        d.add(String(330, y + 2, label, fontName="Review", fontSize=10, fillColor=colors.HexColor(INK)))
    return d


def setup_styles():
    for name, file in [("Review", "Lato-Regular.ttf"), ("ReviewBold", "Lato-Bold.ttf"), ("ReviewItalic", "Lato-Italic.ttf")]:
        pdfmetrics.registerFont(TTFont(name, "/usr/share/fonts/truetype/lato/" + file))
    pdfmetrics.registerFontFamily("Review", normal="Review", bold="ReviewBold", italic="ReviewItalic", boldItalic="ReviewBold")
    styles = getSampleStyleSheet()
    definitions = {
        "Body": dict(fontSize=9.7, leading=14.1, spaceAfter=8),
        "Small": dict(fontSize=8.2, leading=11.4, textColor=colors.HexColor(MUTED), spaceAfter=7),
        "Tiny": dict(fontSize=7.3, leading=9.7, textColor=colors.HexColor(MUTED), spaceAfter=4),
        "TitleR": dict(fontSize=25, leading=29, fontName="ReviewBold", spaceAfter=14),
        "HeadingR": dict(fontSize=18, leading=22, fontName="ReviewBold", spaceAfter=12),
        "SubR": dict(fontSize=11.5, leading=15, fontName="ReviewBold", spaceBefore=7, spaceAfter=6),
        "Cell": dict(fontSize=8.5, leading=11.8, spaceAfter=0),
        "CellSmall": dict(fontSize=8, leading=11, spaceAfter=0),
        "Kicker": dict(fontSize=8.6, leading=12, textColor=colors.HexColor(TEAL), fontName="ReviewBold", spaceAfter=8),
    }
    for name, values in definitions.items():
        base = dict(fontName="Review", textColor=colors.HexColor(INK), alignment=TA_LEFT)
        base.update(values)
        styles.add(ParagraphStyle(name=name, **base))
    return styles


def pdf_report(output, content, ledger, drawing, versions, images):
    pdf = output / "output/pdf/bonsai-release-review.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    styles = setup_styles()
    width = A4[0] - 88
    story = []
    base_url = "http://192.168.1.156:8001/review/"

    def p(text, style="Body"):
        return Paragraph(text, styles[style])

    def t(text, style="Body"):
        return p(escape(text), style)

    def heading(kicker, title):
        story.extend([t(kicker.upper(), "Kicker"), t(title, "HeadingR")])

    def table(headers, rows, widths, small=False):
        data = [[p(f"<b>{escape(h)}</b>", "CellSmall") for h in headers]]
        data += [[t(str(cell), "CellSmall" if small else "Cell") for cell in row] for row in rows]
        item = Table(data, colWidths=widths, hAlign="LEFT", repeatRows=1)
        item.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf3f2")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LINEBELOW", (0, 0), (-1, 0), .8, colors.HexColor(LINE)),
            ("LINEBELOW", (0, 1), (-1, -1), .35, colors.HexColor(LINE)),
        ]))
        return item

    def evidence(item):
        return p('<font color="' + MUTED + '">' + escape(item["evidence_level"]) + '</font> | '
                 '<link href="' + base_url + 'index.html#' + item["id"] + '" color="' + TEAL + '">Finding and evidence</link>', "Tiny")

    story.extend([t("DEVELOPMENT CANDIDATE / 6-7 NOVEMBER 2026", "Kicker"),
                  t(content["question"], "TitleR"), t(content["answer"]),
                  t(content["recommendation"]), Spacer(1, 4), drawing])
    story.append(p("Figure 1. Distinct consolidated findings, not test counts. Fifteen of 56 actionable items remain open; 41 have local fix verification. One additional case was explained. Alias grouping reduces 69 source IDs to 57 items. Priorities are release recommendations, not observed harm. "
                   '<link href="' + base_url + 'data/urgency-counts.json" color="' + TEAL + '">Exact chart data</link> | '
                   '<link href="' + base_url + 'index.html" color="' + TEAL + '">HTML report</link>.', "Small"))
    story.append(table(["Queue", "Open release gates"], [
        ["P0 / 2", "Ingestion role boundary; private-record policy (conditional on a privacy promise)."],
        ["P1 / 4", "Duplicate save/stale feedback; invalid Select all target; missing companion input; stale selected-only export."],
        ["P2 / 7", "Recovery, concurrent edits, misleading count, CSV hardening and unresolved reading-surface scope."],
        ["P3 / 2", "Phone overview overflow and CSV newline normalization."],
    ], [60, width - 60]))
    story.extend([Spacer(1, 10), t(content["scope"], "Small"),
                  p('<b>Status:</b> Local branches only. No push, production deployment or release certification. '
                    'A successful targeted retest does not establish whole-product coverage.', "Small"), PageBreak()])

    heading("Access boundaries / P0", "Resolve the access contract first")
    for item in content["open_findings"][:2]:
        story.extend([t(item["id"], "Kicker"), t(item["title"], "SubR"), t(item["impact"]),
                      p("<b>Observed:</b> " + escape(item["reproduction"])), evidence(item),
                      p("<b>Next action:</b> " + escape(item["action"])),
                      p("<b>Until resolved:</b> " + escape(item["workaround"])),
                      t(item.get("condition", item["recency"]), "Small"), Spacer(1, 12)])
    story.extend([t("Priority meaning", "SubR"), t(content["priority_definitions"]["P0"], "Small"),
                  t("The isolated role test contacted no live API, database or parser. The downstream 201 is a stub response showing that authorization admitted the role; it is not evidence of a completed upload.", "Small"), PageBreak()])

    heading("Affected workflows / P1", "Four workflow gates remain open")
    for item in [f for f in content["open_findings"] if f["priority"] == "P1"]:
        story.append(KeepTogether([t(item["id"], "Kicker"), t(item["title"], "SubR"),
                                  t(item["reproduction"]), p("<b>Next action:</b> " + escape(item["action"])), evidence(item), Spacer(1, 7)]))
    story.extend([t("These priorities apply before the corresponding workflow is enabled. Historical write reproductions were not repeated in the later read-only passes.", "Small"), PageBreak()])

    heading("Deferrable with a decision / P2-P3", "Follow-ups and product-scope choices")
    followups = [f for f in content["open_findings"] if f["priority"] in {"P2", "P3"}]
    story.append(table(["Tier", "Finding", "Decision or next action"],
                       [[f["priority"], f["title"], f["action"]] for f in followups],
                       [43, 178, width - 221], small=True))
    story.extend([Spacer(1, 12), t("CSV formula execution was not attempted. XLSX encoded formula-like labels as data and kept the long leading-zero identifiers as text. The CSV issue is a hardening/compatibility finding, with priority dependent on the intended client workflow.", "Small"),
                  t("The unsupported detail-page warning was corrected locally; support for additional stored result types is still a product decision. Scope decisions are not counted as passing functionality.", "Small"), PageBreak()])

    heading("Coverage and confidence", "Broad software coverage, explicit limits")
    story.append(table(["Area", "Evidence", "Practical limit"],
                       [[row["area"], row["result"], row["limit"]] for row in content["coverage"]],
                       [100, 185, width - 285], small=True))
    story.extend([Spacer(1, 10), p("<b>Configured paths:</b> " + escape(", ".join(content["assay_paths"])) + ".", "Small"),
                  t("Parser coverage: 22 registered keys; 14 formats represented by application fixtures, three more by generic QC examples, and five without application fixtures. Library unit fixtures were tested separately. No claim is made that every supported producer version or species is exhaustively covered.", "Small"),
                  t("Earlier per-phase test totals are not added together. The 320-test inventory carries forward unchanged SDK/API/guard suites and includes the final 62-test frontend rerun. Offline contract observations and browser observations are separate denominators.", "Small"), PageBreak()])

    heading("Locally verified corrections", "41 findings have passing local fixes")
    for item in content["fixed_groups"]:
        story.extend([t(item["title"], "SubR"), t(item["text"])])
    story.extend([Spacer(1, 4), table(["Component", "Local branch / revision"], [
        ["Application", versions["application_branch"] + "\n" + versions["application_fix_commit"]],
        ["Nested SDK", versions["sdk_branch"] + "\n" + versions["sdk_commit"]],
        ["Development base", versions["development_base"]],
    ], [92, width - 92], small=True), Spacer(1, 8),
                  t("These are source revisions, not newly built release images. Application and SDK overlays were tested as a pair. The final report and harness are committed separately from the application fix; exact source hashes are in the review provenance.", "Small"), PageBreak()])

    heading("Screenshots / original files", "Two representative pieces of evidence")
    for item, path in zip(content["screenshots"], images):
        iw, ih = struct.unpack(">II", path.read_bytes()[16:24])
        scale = min(width / iw, 222 / ih)
        story.extend([t(item["title"], "SubR"), Image(str(path), iw * scale, ih * scale, hAlign="LEFT"), Spacer(1, 6),
                      t(item["caption"], "Small"), p('<link href="' + base_url + 'assets/' + path.name + '" color="' + TEAL + '">Open original screenshot at full resolution</link>', "Tiny"), Spacer(1, 10)])
    story.extend([t("Screenshots are unchanged originals from the synthetic local instance. The HTML report links each full-resolution file and the exact JSON evidence.", "Small"), PageBreak()])

    heading("Fresh-instance acceptance route", "Next week's test can start here")
    for n, item in enumerate(content["acceptance_route"], 1):
        story.extend([t(f"{n}. {item['step']}", "SubR"), t(item["check"])])
    story.append(t("What remains outside the claim", "SubR"))
    for item in content["remaining_gaps"]:
        story.append(t(item, "Small"))
    story.extend([p('<b>Evidence and reproducibility:</b> <link href="' + base_url + 'index.html" color="' + TEAL + '">Phone-friendly report</link> | '
                    '<link href="' + base_url + 'data/findings-ledger.json" color="' + TEAL + '">Complete finding ledger</link> | '
                    '<link href="' + base_url + 'technical.html" color="' + TEAL + '">Methods and provenance</link> | '
                    '<link href="http://192.168.1.156:8001/" color="' + TEAL + '">Detailed phase report</link>.', "Small")])

    def decorate(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor(LINE)); canvas.setLineWidth(.6)
        canvas.line(44, A4[1] - 33, A4[0] - 44, A4[1] - 33)
        canvas.setFont("ReviewBold", 8); canvas.setFillColor(colors.HexColor(TEAL))
        canvas.drawString(44, A4[1] - 25, "BONSAI / DEVELOPMENT RELEASE-TEST REVIEW")
        canvas.setFont("Review", 8); canvas.setFillColor(colors.HexColor(MUTED))
        canvas.drawString(44, 25, "Synthetic local instance | 7 November 2026 | Local fixes require a fresh build and retest")
        canvas.drawRightString(A4[0] - 44, 25, str(doc.page))
        canvas.restoreState()

    doc = BaseDocTemplate(str(pdf), pagesize=A4, leftMargin=44, rightMargin=44, topMargin=48, bottomMargin=43,
                          title=content["title"], author="Bonsai development test review", subject=content["question"])
    frame = Frame(44, 43, width, A4[1] - 91, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates(PageTemplate(id="Review", frames=frame, onPage=decorate))
    doc.build(story)
    return pdf


CSS = """
:root{--ink:#193740;--muted:#536b73;--teal:#23685f;--line:#d8e2e2;--paper:#fff;--bg:#f1f5f4}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;color:var(--ink);background:var(--bg);font:16px/1.6 system-ui,sans-serif}a{color:var(--teal);text-underline-offset:3px;overflow-wrap:anywhere}header,main,footer{max-width:1060px;margin:auto;padding:28px}header{padding-top:40px}h1{font-size:clamp(1.9rem,4vw,2.8rem);line-height:1.15;letter-spacing:-.03em;max-width:850px}h2{font-size:1.55rem;line-height:1.25;margin:0 0 18px}h3{font-size:1.1rem;line-height:1.35;margin:10px 0}.eyebrow,.id{font-size:.78rem;font-weight:750;color:var(--teal);letter-spacing:.04em}.lead{font-size:1.13rem;max-width:900px}.note,figcaption{font-size:.88rem;color:var(--muted)}nav,.actions{display:flex;gap:10px;flex-wrap:wrap;margin:22px 0}nav a,.actions a{padding:9px 13px;background:white;border:1px solid var(--line);border-radius:8px;text-decoration:none;min-height:44px}.actions a.primary{background:var(--teal);color:white;border-color:var(--teal)}section{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:26px;margin-bottom:26px;scroll-margin-top:18px}.callout{border-left:4px solid #a73145;padding:10px 18px;background:#fff7f8;margin:20px 0}.chart{display:block;width:100%;max-width:760px;height:auto}figure{margin:20px 0}figcaption{margin-top:9px}.row{display:grid;grid-template-columns:1fr 1fr;gap:22px}.finding{border-top:1px solid var(--line);padding:22px 0;scroll-margin-top:16px}.finding:first-of-type{border-top:0}.priority{display:inline-block;padding:3px 8px;border-radius:4px;font-size:.78rem;font-weight:800;color:white;margin-right:8px}.p0{background:#a73145}.p1{background:#b66220}.p2{background:#366ba0}.p3{background:#6e7c86}.finding p{margin:9px 0}.finding .id{overflow-wrap:anywhere}.evidence{font-size:.83rem;color:var(--muted)}.links{display:flex;gap:8px 18px;flex-wrap:wrap;font-size:.85rem}details{border-top:1px solid var(--line);margin-top:12px;padding-top:12px}summary{cursor:pointer;font-weight:650;min-height:36px}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;font-size:.88rem}th,td{text-align:left;vertical-align:top;padding:10px 9px;border-bottom:1px solid var(--line)}th{background:#edf3f2;font-size:.8rem}td:first-child{font-weight:650}code{font-size:.84em;overflow-wrap:anywhere}.screens img{display:block;width:100%;height:auto;border:1px solid var(--line);border-radius:8px}.screens a{display:block}.step{margin-bottom:18px}.step p{margin-top:5px}.fixed{color:var(--teal)}.ledger{font-size:.85rem}.ledger article{padding:14px 0;border-bottom:1px solid var(--line)}footer{font-size:.85rem;color:var(--muted)}
@media(max-width:650px){header,main,footer{padding:20px 16px}header{padding-top:26px}section{padding:20px 16px}.row{display:block}nav a{font-size:.85rem}h2{font-size:1.35rem}.table-wrap{margin:0 -8px}th,td{padding:9px 7px}table{min-width:620px}.priority-table{min-width:0}.priority-table td:first-child{width:58px}.chart{max-width:340px}.followup-table{min-width:680px}}
@page{size:A4;margin:16mm} @media print{body{background:white;font-size:10pt}header,main,footer{max-width:none;padding:0}nav,.actions{display:none}section{border:0;border-radius:0;padding:0;margin:20px 0;break-before:page}section:first-child{break-before:auto}.finding{break-inside:avoid}.row{display:block}.screens img{max-height:85mm;width:auto;max-width:100%}.table-wrap{overflow:visible}table{min-width:0!important;font-size:8pt}.ledger{display:none}a{color:inherit}.note,figcaption{font-size:8pt}}
"""


def html_report(output, content, ledger, published, versions):
    esc = escape

    def link_evidence(item):
        return '<div class="links">' + ''.join('<a href="' + published[path] + '">' + esc(Path(path).name + " / " + path.split('/')[0]) + '</a>' for path in item["evidence"]) + '</div>'

    def finding(item, compact=False):
        head = '<article class="finding" id="' + item["id"] + '"><span class="priority ' + item["priority"].lower() + '">' + item["priority"] + '</span><span class="id">' + item["id"] + '</span><h3>' + esc(item["title"]) + '</h3>'
        body = '<p>' + esc(item["impact"]) + '</p><p><strong>Next action:</strong> ' + esc(item["action"]) + '</p>'
        detail = '<p><strong>Observed:</strong> ' + esc(item["reproduction"]) + '</p>'
        if item.get("workaround"):
            detail += '<p><strong>Until resolved:</strong> ' + esc(item["workaround"]) + '</p>'
        if item.get("condition"):
            detail += '<p>' + esc(item["condition"]) + '</p>'
        detail += '<p class="evidence">' + esc(item["evidence_level"]) + (". " + esc(item["recency"]) if item.get("recency") else "") + '.</p>' + link_evidence(item)
        if compact:
            detail = '<details><summary>Reproduction and evidence</summary>' + detail + '</details>'
        return head + body + detail + '</article>'

    def table(headers, rows, cls=""):
        return '<div class="table-wrap"><table class="' + cls + '"><thead><tr>' + ''.join('<th scope="col">' + esc(h) + '</th>' for h in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join('<td>' + esc(str(c)) + '</td>' for c in row) + '</tr>' for row in rows) + '</tbody></table></div>'

    caption = "Figure 1. Distinct consolidated findings, not test counts: 15 open and 41 fixed locally among 56 actionable items; one additional case explained. Related phase IDs were grouped explicitly (69 source IDs to 57 items). Priorities are recommendations; the privacy gate is conditional on the release contract."
    sections = ['<section id="decision"><h2>What is the release decision?</h2><p>' + esc(content["recommendation"]) + '</p><figure><picture><source media="(max-width:650px)" srcset="assets/urgency-mobile.svg" width="280" height="290"><img class="chart" src="assets/urgency.svg" width="480" height="165" alt="Open by urgency: P0 2, P1 4, P2 7, P3 2. Status: 41 fixed locally, 15 open, one explained."></picture><figcaption>' + caption + ' <a href="data/urgency-counts.json">Exact chart data</a> | <a href="data/findings-ledger.json">Complete ledger</a>.</figcaption></figure><div class="callout"><strong>Local verification is not deployment.</strong> The fixes are on paired local branches. A clean build and fresh-instance retest are still required.</div>' + table(["Priority", "Meaning"], content["priority_definitions"].items(), "priority-table") + '</section>']
    for priority, title in [("P0", "Access-policy gates"), ("P1", "Workflow gates")]:
        sections.append('<section id="' + priority.lower() + '"><h2>' + priority + ': ' + title + '</h2>' + ''.join(finding(item) for item in content["open_findings"] if item["priority"] == priority) + '</section>')
    sections.append('<section id="followups"><h2>P2-P3: follow-ups and scope decisions</h2><p>These can be deferred only with an explicit product decision or usable workaround. Advertised reading surfaces, untrusted CSV use or required phone operation can raise the recommended priority.</p>' + ''.join(finding(item, True) for item in content["open_findings"] if item["priority"] in {"P2", "P3"}) + '</section>')
    sections.append('<section id="coverage"><h2>How comprehensive was the testing?</h2>' + table(["Area", "Evidence", "Practical limit"], [[r["area"], r["result"], r["limit"]] for r in content["coverage"]]) + '<p class="note"><strong>Configured paths:</strong> ' + esc(", ".join(content["assay_paths"])) + '. Eight paths include aliases. There are 22 registered parser keys: 14 application-fixture formats, three additional generic QC examples and five without application fixtures. SDK library fixtures were tested separately.</p><p class="note">Earlier per-phase totals are not summed. The 320 selected automated tests are a suite inventory; only the 62 frontend tests were rerun after the final template-only correction. Offline contracts and browser checks have separate denominators.</p><div class="links"><a href="' + published[f"{PARSER}/coverage.json"] + '">Parser coverage matrix</a><a href="' + published[f"{PARSER}/regressions.json"] + '">Prior suite evidence (314)</a><a href="technical.html#verification">Final rerun evidence (62 frontend)</a></div></section>')
    sections.append('<section id="fixed"><h2>41 findings fixed locally</h2><div class="row">' + ''.join('<div><h3>' + esc(r["title"]) + '</h3><p>' + esc(r["text"]) + '</p></div>' for r in content["fixed_groups"]) + '</div><p class="note">The item-by-item fixed list and original aliases are retained below. Open partial-scope issues are not counted as fixed.</p>' + table(["Component", "Branch", "Source revision"], [["Application", versions["application_branch"], versions["application_fix_commit"]], ["Nested SDK", versions["sdk_branch"], versions["sdk_commit"]]]) + '</section>')
    sections.append('<section class="screens" id="screenshots"><h2>Representative screenshots</h2>' + ''.join('<figure><h3>' + esc(s["title"]) + '</h3><a href="assets/' + Path(s["path"]).name + '" target="_blank" rel="noopener"><img src="assets/' + Path(s["path"]).name + '" alt="' + esc(s["title"]) + '" loading="lazy"></a><figcaption>' + esc(s["caption"]) + ' Tap the image for the original full-resolution PNG.</figcaption></figure>' for s in content["screenshots"]) + '</section>')
    sections.append('<section id="next"><h2>Fresh-instance acceptance route</h2>' + ''.join('<div class="step"><h3>' + str(n) + '. ' + esc(r["step"]) + '</h3><p>' + esc(r["check"]) + '</p></div>' for n, r in enumerate(content["acceptance_route"], 1)) + '<h3>Remaining gaps</h3><ul>' + ''.join('<li>' + esc(item) + '</li>' for item in content["remaining_gaps"]) + '</ul></section>')
    sections.append('<section id="ledger" class="ledger"><h2>Complete current finding ledger</h2><p>Every historical ID is mapped to a current item. The explained case is separate from actionable findings. The displayed detail below is intentionally secondary to the prioritized queue.</p><details><summary>Show all 57 consolidated items</summary>' + ''.join('<article><span class="id">' + esc(item["id"]) + '</span><h3>' + esc(item["title"]) + '</h3><p><strong>' + esc(item["status"].replace('_', ' ')) + '</strong>' + (' / ' + item["priority"] if item["priority"] else '') + ': ' + esc(item.get("summary", item.get("impact", ""))) + '</p><p class="note">Source IDs: ' + esc(", ".join(item["source_ids"])) + '</p>' + link_evidence(item) + '</article>' for item in ledger["findings"]) + '</details></section>')
    header = '<p class="eyebrow">BONSAI / DEVELOPMENT REVIEW / 6-7 NOVEMBER 2026</p><h1>' + esc(content["question"]) + '</h1><p class="lead">' + esc(content["answer"]) + '</p><p class="note">' + esc(content["scope"]) + '</p><div class="actions"><a class="primary" href="output/pdf/bonsai-release-review.pdf">Download the 8-page PDF</a><a href="../index.html">Detailed phase findings</a><a href="technical.html">Methods and provenance</a></div><nav aria-label="Report sections">' + ''.join('<a href="#' + target + '">' + title + '</a>' for target, title in [("decision", "Decision"), ("p0", "P0 access"), ("p1", "P1 workflows"), ("followups", "Follow-ups"), ("coverage", "Coverage"), ("fixed", "Local fixes"), ("screenshots", "Screenshots"), ("next", "Next week's route")]) + '</nav>'
    page = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + esc(content["title"]) + '</title><style>' + CSS + '</style></head><body><header>' + header + '</header><main>' + ''.join(sections) + '</main><footer>Compiled 7 November 2026. Synthetic local instance; no production deployment. <a href="provenance.json">Build provenance</a>.</footer><script>addEventListener("beforeprint",()=>document.querySelectorAll("details").forEach(e=>e.open=true));</script></body></html>'
    (output / "index.html").write_text(page)


def build(run, output):
    run, output = run.resolve(), output.resolve()
    external = (DATA).resolve()
    if not output.is_relative_to(external) or output.is_relative_to(run) or run.is_relative_to(output):
        raise ValueError("Choose a separate output directory on the external Bonsai data drive")
    output.mkdir(parents=True, exist_ok=True)
    content = read(CONTENT)
    ledger = consolidate(run, content)
    versions = {
        "application_branch": git_at(REPO, "branch", "--show-current"),
        "application_fix_commit": read(run / AUDIT / "context.json")["application_fix_commit"],
        "sdk_branch": git_at(REPO / "bonsai-sdk", "branch", "--show-current"),
        "sdk_commit": git_at(REPO / "bonsai-sdk", "rev-parse", "HEAD"),
        "development_base": "21eccf7075fb59a897cb2ae86b0d6cdb95d0089c",
        "report_source_commit": git_at(REPO, "rev-parse", "HEAD"),
    }
    published, receipts = {}, {}
    evidence_files = set(SOURCE_FILES + EXTRA_EVIDENCE)
    for item in ledger["findings"]:
        evidence_files.update(item["evidence"])
    for relative in sorted(evidence_files):
        source = (run / relative).resolve()
        if not source.is_relative_to(run) or source.suffix != ".json":
            raise ValueError(f"Not approved public evidence: {relative}")
        raw = source.read_bytes()
        if TOKEN.search(raw):
            raise ValueError(f"Token-shaped data refused: {relative}")
        target = output / "evidence" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        published[relative] = "evidence/" + relative
        receipts[relative] = {"sha256": digest(source), "bytes": len(raw)}
    assets = output / "assets"
    assets.mkdir(exist_ok=True)
    images = []
    for item in content["screenshots"]:
        source = (run / item["path"]).resolve()
        if not source.is_relative_to(run) or source.suffix != ".png" or source.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError("Only original PNG screenshots may be published")
        target = assets / source.name
        shutil.copy2(source, target); images.append(target)
        receipts[item["path"]] = {"sha256": digest(source), "bytes": source.stat().st_size}
    setup_styles()
    drawing = chart(ledger)
    for name, figure in [("urgency.svg", drawing), ("urgency-mobile.svg", chart(ledger, mobile=True))]:
        renderSVG.drawToFile(figure, str(assets / name))
        svg = (assets / name).read_text()
        svg = re.sub(r"<!DOCTYPE.*?>", "", svg, flags=re.S)
        svg = svg.replace("font-family: ReviewBold;", "font-family: sans-serif; font-weight: 700;")
        svg = svg.replace("font-family: Review;", "font-family: sans-serif;")
        svg = svg.replace("<title>...</title>", "<title>Consolidated findings by urgency and current status</title>")
        svg = svg.replace("<desc>...</desc>", "<desc>Open: P0 two, P1 four, P2 seven, P3 two. Status: 41 fixed locally, 15 open, one explained.</desc>")
        (assets / name).write_text(svg)
    write_json(output / "data/findings-ledger.json", ledger)
    write_json(output / "data/urgency-counts.json", {"unit": "consolidated finding", "open_by_priority": ledger["open_by_priority"], "status": ledger["counts"], "actionable_denominator": 56, "all_items": 57, "limitations": ledger["counting_rule"]})
    pdf = pdf_report(output, content, ledger, drawing, versions, images)
    html_report(output, content, ledger, published, versions)
    audit = read(run / AUDIT / "context.json")
    state = read(run / AUDIT / "state-verification.json")
    verification = {"frontend_passed": 62, "focused_sidebar_passed": 6,
                    "log_sha256": digest(run / AUDIT / "frontend-after.log"),
                    "focused_log_sha256": digest(run / AUDIT / "sidebar-context-after.log"),
                    "source_test": "frontend/tests/test_sidebar_context.py",
                    "carried_forward_suites": {"sdk": 196, "api": 45, "scope_guards": 17},
                    "suite_inventory": 320, "original_data_preserved": state["all_original_collections_unchanged"]}
    # Ensure the asserted rerun count is actually present in the saved log.
    if not re.search(r"\b62 passed\b", (run / AUDIT / "frontend-after.log").read_text()):
        raise ValueError("The final frontend rerun does not support the authored result")
    write_json(output / "data/final-verification.json", verification)
    build_cmd = "python scripts/build_release_review.py --run-dir ~/data/codex/bonsai/runs/2026-11-06-species-ui --output ~/data/codex/bonsai/docs/development-findings/review"
    technical = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bonsai review methods</title><style>' + CSS + '</style></head><body><header><p class="eyebrow">TECHNICAL NOTE / 7 NOVEMBER 2026</p><h1>Evidence, counting and reproducibility</h1><p><a href="index.html">Return to the prioritized review</a></p></header><main><section><h2>Method and scope</h2><p>' + escape(content["scope"]) + '</p><p>The final gap audit used local Chromium/Selenium with disposable generic records. Analysis/curation mutations were blocked. The authorization audit used the real router and token/role checks in a network-disabled container, with user lookup and downstream execution stubbed.</p><p>Ten disposable records and one group were removed. Before/after collection hashes match for the 125 original records, 459 analysis documents, eight curation documents, 12 groups and four users. Workers were restored.</p><p><a href="' + published[f"{AUDIT}/state-verification.json"] + '">Exact state verification</a> | <a href="' + published[f"{AUDIT}/context.json"] + '">Audit context and harness corrections</a></p></section><section><h2>How the ledger is counted</h2><p>' + escape(ledger["counting_rule"]) + '</p><p>Sixty-five unique historical IDs plus four new IDs become 57 consolidated items after 12 explicit alias merges. There are 56 actionable items (41 fixed locally and 15 open) and one explained baseline case. The corrected unavailable-result message remains part of an open scope item, so it is not counted twice.</p><p><a href="data/findings-ledger.json">Full ledger, aliases, original states and current decisions</a></p></section><section id="verification"><h2>Final regression and source evidence</h2><p>The new sidebar regression is fixed at application revision <code>' + versions["application_fix_commit"] + '</code>. Six role-aware summary/metadata/detail checks pass, and all 62 frontend tests pass. The previously passing 196 SDK, 45 API and 17 guard tests are carried forward after this template-only change; they were not all rerun. Log hashes allow the private operational logs to be matched without publishing them.</p><p><a href="data/final-verification.json">Exact final verification summary and log hashes</a></p><p>The current paired SDK branch is <code>' + versions["sdk_branch"] + '</code> at <code>' + versions["sdk_commit"] + '</code>. Start the source-overlay stack with <code>bash scripts/parser-display-test.sh up</code>. Release images must be rebuilt separately.</p></section><section><h2>Rebuilding this reading surface</h2><p>Authored content: <code>docs/local-testing/release-review-content.json</code>. Builder: <code>scripts/build_release_review.py</code>. The builder requires ReportLab and Lato fonts; generated artifacts belong on the data drive.</p><p><code>' + escape(build_cmd) + '</code></p><p>The installed reporting dependencies are external at <code>~/data/codex/bonsai/environments/reporting-deps</code> and are used with the Python 3.11 test image. Render the PDF with Poppler and visually check every page after any content change.</p><p>The earlier detailed report is preserved in the sibling archive <code>development-findings-through-parsers-2026-11-07</code>. Only whitelisted JSON/PNG evidence is copied; browser DOM, JWT-bearing pages, raw logs, profiles and database payloads are not published.</p><p><a href="provenance.json">Source hashes and public artifact manifest</a> | <a href="../index.html">Detailed phase report</a></p></section></main></body></html>'
    (output / "technical.html").write_text(technical)
    provenance = {"created_at": datetime.now(timezone.utc).isoformat(), "versions": versions,
                  "audit_completed_at": audit["completed_testing_at"], "counting": {key: value for key, value in ledger.items() if key != "findings"},
                  "verification": verification, "evidence": receipts,
                  "authoring_sources": {str(path.relative_to(REPO)): digest(path) for path in [CONTENT, Path(__file__)]},
                  "operational_sources": {str(path.relative_to(REPO)): digest(path) for path in [REPO / "scripts/check_release_gaps.py", REPO / "scripts/check_release_permission_gate.py", REPO / "frontend/tests/test_sidebar_context.py"]},
                  "public_artifacts": {str(path.relative_to(output)): {"sha256": digest(path), "bytes": path.stat().st_size} for path in output.rglob("*") if path.is_file() and path.name != "provenance.json"}}
    write_json(output / "provenance.json", provenance)
    print(json.dumps({"html": str(output / "index.html"), "pdf": str(pdf), "counts": ledger["counts"], "open_by_priority": ledger["open_by_priority"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=DATA / "runs/2026-11-06-species-ui")
    parser.add_argument("--output", type=Path, default=DATA / "docs/development-findings/review")
    args = parser.parse_args()
    build(args.run_dir, args.output)
