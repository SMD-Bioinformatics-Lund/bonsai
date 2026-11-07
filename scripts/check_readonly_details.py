"""Observed read-only checks for existing species fixtures; use with the Selenium session."""

from collections import Counter
from datetime import datetime, timezone
import csv
from fnmatch import fnmatch
import hashlib
import io
import json
from pathlib import Path
from urllib.parse import urlsplit

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC

from check_general_fix_browser import GeneralUI
from detail_readonly_scope import FORM_GUARD, ReadOnlyDetailScope


class DetailUI(GeneralUI):
    def __init__(self, browser, args, api, phase="baseline"):
        from selenium.webdriver.support.ui import WebDriverWait
        self.browser, self.args, self.api = browser, args, api
        self.scope = ReadOnlyDetailScope()
        self.wait = WebDriverWait(browser, 15)
        self.phase = phase
        self.root = args.run_dir.resolve() / "detail-read/2026-11-07"
        self.requests = {}
        self.catalog = json.loads((args.run_dir / "fixtures/expectations.json").read_text())["samples"]
        browser.execute_cdp_cmd("Network.enable", {})
        self.blocked_urls = self.scope.config["browser_blocked_urls"] + ["*://localhost:18000/*/igv*", "*://localhost:18000/sample/*/similar*"]
        browser.execute_cdp_cmd("Network.setBlockedURLs", {"urls": self.blocked_urls})
        browser.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": FORM_GUARD})

    def prepare(self):
        if (self.root / "expectations.json").exists():
            raise ValueError("Preserve completed expectations; use load() for a retest")
        identities = self.api.request("/samples/summary", data={"fields": ["sample_id", "external_sample_id"], "limit": 0, "offset": 0})["data"]
        ids = {r["external_sample_id"]: r["sample_id"] for r in identities}
        expected, dismissed = {}, {}
        for case in self.catalog:
            sample = self.api.request("/samples/" + ids[case["sample_id"]])
            results = [r for r in sample["element_type_result"] if r["software"] == "tbprofiler" and r["analysis_type"] == "amr"]
            variants = [v for r in results for v in (r.get("result") or {}).get("variants", [])]
            dismissed[case["sample_id"]] = [c["result_key"] for r in results for c in r.get("curations", [])
                if c.get("annotation_type") == "variant" and c.get("decision") == "reject"]
            expected[case["sample_id"]] = {"internal_id": ids[case["sample_id"]], "sample_name": case["sample_name"],
                "lims_id": case["lims_id"], "assay": case["assay"], "metadata_fields": [m["fieldname"] for m in sample["metadata"]],
                "has_detail_result": any(r.get("result") is not None for r in results),
                "rows": [{k: v.get(k) for k in ("id", "depth", "frequency", "reference_sequence", "start")} for v in variants]}
        (self.root / "expectations.json").write_text(json.dumps(expected, indent=2) + "\n")
        (self.root / "curation-display-expectations.json").write_text(json.dumps(dismissed, indent=2) + "\n")
        self.expected = expected
        self.dismissed = dismissed

    def load(self):
        self.expected = json.loads((self.root / "expectations.json").read_text())
        self.dismissed = json.loads((self.root / "curation-display-expectations.json").read_text())

    def audit(self):
        for entry in self.browser.get_log("performance"):
            message = json.loads(entry["message"])["message"]
            p = message["params"]
            if message["method"] == "Network.requestWillBeSent":
                request = p["request"]
                url = urlsplit(request["url"])
                if url.netloc not in {"localhost:18000", "localhost:18001"}:
                    continue
                blocked = any(fnmatch(request["url"], pattern) for pattern in self.blocked_urls)
                if blocked:
                    pass  # Network.setBlockedURLs prevents these automatic requests.
                elif url.port == 18000:
                    self.scope.check_browser(request["method"], url.path, request.get("postData", ""))
                else:
                    self.scope.check(request["method"], url.path)
                self.requests[p["requestId"]] = {"method": request["method"], "path": url.path,
                    "service": "frontend" if url.port == 18000 else "api", "status": None, "blocked_by_harness": blocked}
            elif message["method"] == "Network.responseReceived" and p["requestId"] in self.requests:
                self.requests[p["requestId"]]["status"] = p["response"]["status"]
                if self.requests[p["requestId"]]["blocked_by_harness"]:
                    raise RuntimeError("An excluded request unexpectedly received a response")
        (self.root / (self.phase + "-browser-requests.json")).write_text(json.dumps(list(self.requests.values()), indent=2) + "\n")

    def capture(self, name, sid):
        directory = self.root / "browser" / self.phase / self.args.role
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / (name + "-" + sid + ".png")
        self.browser.save_screenshot(str(path))
        path.with_suffix(".html").write_text(self.browser.page_source)
        path.with_suffix(".console.json").write_text(json.dumps(self.browser.get_log("browser"), indent=2))
        return str(path.relative_to(self.args.run_dir.resolve()))

    def log(self, name, status, expected, observed, sid, *, screenshot=False, surface="browser"):
        if isinstance(status, bool):
            status = "PASS" if status else "FAIL"
        artifact = self.capture(name, sid) if surface == "browser" and (screenshot or status == "FAIL") else None
        item = {"time": datetime.now(timezone.utc).isoformat(), "increment": "read-only-details", "phase": self.phase,
            "surface": surface, "role": self.api.username if surface == "api" else self.args.role, "case": name, "sample": sid, "assay": self.expected[sid]["assay"],
            "status": status, "expected": expected, "observed": observed, "artifact": artifact,
            "url": self.browser.current_url if surface == "browser" else None}
        with (self.root / "results.jsonl").open("a") as handle:
            handle.write(json.dumps(item) + "\n")
        if status == "FAIL":
            print(name, sid, status)
        return item

    def identity(self, sid):
        body = self.browser.find_element(By.TAG_NAME, "body").text
        row = self.expected[sid]
        return "500" not in self.browser.title and all(x in body for x in (sid, row["sample_name"], row["lims_id"]))

    def detail_url(self, sid):
        return self.args.url + "/sample/" + self.expected[sid]["internal_id"] + "/resistance/variants"

    def row_ids(self):
        return [e.get_attribute("data-variant-id") for e in self.browser.find_elements(By.CSS_SELECTOR,
            '#tb-profiler-variant-tbl tbody input[data-variant-id]')]

    def navigation(self):
        self.login("user_one")
        for case in self.catalog:
            sid, expected = case["sample_id"], self.expected[case["sample_id"]]
            self.browser.get(self.args.url + "/sample/" + expected["internal_id"])
            self.click(self.browser.find_element(By.LINK_TEXT, "Variants"))
            available = self.identity(sid)
            self.log("detail-page-identity", available, "The linked detail page keeps all three saved record identifiers",
                {"title": self.browser.title, "identity_matches": available}, sid, screenshot=sid.endswith("_001"))
            if available:
                expected_ids = sorted(str(r["id"]) for r in expected["rows"])
                self.log("detail-stored-row-identities", sorted(self.row_ids()) == expected_ids,
                    "Displayed row identifiers equal the existing stored detail rows", {"expected_rows": len(expected_ids), "displayed_rows": len(self.row_ids())}, sid)
                if not expected["has_detail_result"]:
                    body = self.browser.find_element(By.TAG_NAME, "body").text
                    self.log("detail-unavailable-state", "No predicted resistance determinants" not in body and
                        any(text in body.lower() for text in ("not available", "no stored", "not supported")),
                        "An unavailable detail result is labelled as unavailable", {"body_excerpt": body[-900:]}, sid,
                        screenshot=sid.endswith("_001"))
                self.click(self.browser.find_element(By.LINK_TEXT, "Summary"))
            else:
                self.browser.back()
            self.log("return-summary-identity", self.identity(sid), "Returning from details preserves record identity",
                {"identity_matches": self.identity(sid)}, sid)
            self.click(self.browser.find_element(By.LINK_TEXT, "Metadata"))
            body = self.browser.find_element(By.TAG_NAME, "body").text
            missing = [f for f in expected["metadata_fields"] if f not in body]
            self.log("metadata-identity-and-fields", self.identity(sid) and not missing,
                "Metadata keeps the same record identity and every stored field name", {"identity_matches": self.identity(sid), "missing_fields": missing}, sid)
            self.browser.back()
            self.log("history-summary-identity", self.identity(sid), "Browser Back returns to the same summary",
                {"identity_matches": self.identity(sid)}, sid)
            self.audit()
        print("Navigation sweep completed", len(self.catalog))

    def apply_filter(self, sid, values):
        for field, value in values.items():
            element = self.browser.find_element(By.NAME, field)
            if element.get_attribute("type") == "checkbox":
                if element.is_selected() != value:
                    self.click(element)
            else:
                element.clear()
                element.send_keys(str(value))
        old = self.browser.find_element(By.TAG_NAME, "body")
        self.click(self.button("Filter variants"))
        self.wait.until(EC.staleness_of(old))

    def filters(self):
        for case in self.catalog:
            sid = case["sample_id"]
            if not sid.endswith(("_001", "_002", "_010")):
                continue
            self.browser.get(self.detail_url(sid))
            if not self.identity(sid):
                self.log("filter-availability", "N/A", "Only an available detail page can exercise its filter form",
                    {"reason": "Detail page failed before filter interaction"}, sid)
                continue
            self.apply_filter(sid, {"min-depth": 1000000})
            self.log("depth-filter-empty-state", self.identity(sid) and not self.row_ids(),
                "A display-only depth filter above every saved value returns zero rows without a server error",
                {"title": self.browser.title, "displayed_rows": len(self.row_ids())}, sid, screenshot=sid.endswith("_001"))
            self.browser.get(self.detail_url(sid))
            if sid.startswith("synthetic_tb_") and self.expected[sid]["rows"]:
                self.apply_filter(sid, {"min-frequency": 100, "min-depth": 1})
                self.log("combined-filter-intersection", self.identity(sid) and not self.row_ids(),
                    "Combined display filters keep only rows satisfying both saved numeric conditions",
                    {"title": self.browser.title, "displayed_rows": len(self.row_ids())}, sid)
                self.browser.get(self.detail_url(sid))
                self.click(self.browser.find_element(By.ID, "hide-dismissed"))
                old = self.browser.find_element(By.TAG_NAME, "body")
                self.click(self.button("Filter variants"))
                self.wait.until(EC.staleness_of(old))
                expected_ids = sorted(str(r["id"]) for r in self.expected[sid]["rows"] if str(r["id"]) not in self.dismissed.get(sid, []))
                self.log("dismissed-filter-availability", self.identity(sid) and sorted(self.row_ids()) == expected_ids,
                    "The offered display filter hides exactly the rows with existing rejected decisions",
                    {"title": self.browser.title, "displayed_rows": len(self.row_ids()), "expected_rows": len(expected_ids)}, sid)
            self.audit()
        print("Representative filter checks completed")

    def table_interactions(self):
        for case in self.catalog:
            sid = case["sample_id"]
            if not sid.startswith("synthetic_tb_") or not self.expected[sid]["rows"]:
                continue
            self.browser.get(self.detail_url(sid))
            if not self.identity(sid):
                continue
            search = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.dt-search input')))
            search.send_keys("__absent_detail_row__")
            self.wait.until(lambda _: not self.row_ids())
            self.log("table-search-empty", "No matching records found" in self.browser.find_element(By.TAG_NAME, "body").text,
                "A search without matches clearly reports an empty filtered table", {"rows": len(self.row_ids())}, sid)
            search.clear()
            search.send_keys(Keys.SPACE, Keys.BACKSPACE)
            self.wait.until(lambda _: len(self.row_ids()) == len(self.expected[sid]["rows"]))
            self.log("table-search-reset", sorted(self.row_ids()) == sorted(str(r["id"]) for r in self.expected[sid]["rows"]),
                "Clearing table search restores every saved row", {"rows": len(self.row_ids())}, sid)
            start = next(e for e in self.browser.find_elements(By.CSS_SELECTOR, '#tb-profiler-variant-tbl thead td') if e.text.strip() == "Start")
            self.click(start)
            asc = [str(r["id"]) for r in sorted(self.expected[sid]["rows"], key=lambda r: r["start"])]
            self.wait.until(lambda _: self.row_ids() == asc)
            self.log("table-sort-start", self.row_ids() == asc, "Start-column sorting follows saved numeric values", {"rows": len(self.row_ids())}, sid)
            self.log("table-pagination", "N/A", "Pagination is checked only when the product offers it", {"reason": "Detail tables intentionally disable pagination"}, sid)
            self.audit()
        print("Table search and sort completed")

    def api_exports(self, sample_ids=None):
        directory = self.root / "exports"
        directory.mkdir(exist_ok=True)
        for case in self.catalog:
            sid = case["sample_id"]
            if sample_ids is not None and sid not in sample_ids:
                continue
            for fmt, delimiter in [("tsv", "\t"), ("csv", ",")]:
                result = self.api.request("/export/" + self.expected[sid]["internal_id"] + "/lims?fmt=" + fmt, expected=(200, 422, 500))
                status = self.api.last_status
                observed = {"http_status": status}
                ok = status == 422 and isinstance(result, dict) and bool(result.get("detail"))
                if status == 200:
                    rows = list(csv.reader(io.StringIO(result), delimiter=delimiter))
                    ok = rows[0] == ["sample_id", "parameter_name", "parameter_value", "comment"] and len(rows) > 1 and all(r[0] == case["sample_name"] and len(r) == 4 for r in rows[1:])
                    path = directory / (sid + "." + fmt)
                    path.write_text(result)
                    observed.update(rows=len(rows)-1, same_record=all(r[0] == case["sample_name"] for r in rows[1:]),
                        sha256=hashlib.sha256(result.encode()).hexdigest())
                self.log("export-" + fmt + "-structure", ok, "An available export has the correct file structure and saved record identity; unavailable exports give explicit validation feedback",
                    observed, sid, surface="api")
        print("Export format sweep completed")

    def browser_exports(self):
        directory = self.args.run_dir.resolve() / "browser-results/user_one" / self.args.session_name / "downloads"
        directory.mkdir(exist_ok=True)
        for case in self.catalog:
            sid = case["sample_id"]
            if not sid.endswith("_001"):
                continue
            self.browser.get(self.detail_url(sid))
            if not self.identity(sid):
                continue
            before = set(directory.glob("*"))
            old_url = self.browser.current_url
            self.click(self.button("Export to LIMS"))
            state = self.wait.until(lambda _: next((p for p in directory.glob("*.txt") if p not in before and p.stat().st_size), None)
                or (self.browser.current_url != old_url and self.browser.current_url))
            if isinstance(state, Path):
                rows = list(csv.reader(io.StringIO(state.read_text()), delimiter="\t"))
                ok = len(rows) > 1 and all(r[0] == case["sample_name"] for r in rows[1:])
                observed = {"downloaded": True, "rows": len(rows)-1, "same_record": ok}
            else:
                body = self.browser.find_element(By.TAG_NAME, "body").text
                ok = self.identity(sid) and any(x in body.lower() for x in ("not supported", "not present", "not implemented"))
                observed = {"downloaded": False, "title": self.browser.title, "clear_unavailable_feedback": ok}
            self.log("browser-export-or-feedback", ok, "Export downloads the current record or explains its unavailability", observed, sid, screenshot=True)
            self.audit()
        print("Browser export checks completed")

    def role_and_history(self):
        representatives = [c["sample_id"] for c in self.catalog if c["sample_id"].endswith("_001")]
        for role in ("admin", "user_two"):
            self.login(role)
            for sid in representatives:
                self.browser.get(self.detail_url(sid))
                self.log("public-detail-role-access", self.identity(sid), "The existing public detail record opens for this authorized account",
                    {"identity_matches": self.identity(sid)}, sid, screenshot=sid == representatives[0])
                self.audit()
        self.login("user_one")
        for i, sid in enumerate(representatives):
            other = representatives[(i + 1) % len(representatives)]
            self.browser.get(self.detail_url(sid))
            self.browser.get(self.detail_url(other))
            other_matches = self.identity(other)
            self.browser.back()
            self.log("cross-record-history-identity", other_matches and self.identity(sid),
                "Moving between two records and returning with Back keeps the right saved identity",
                {"second_record_matches": other_matches, "returned_record_matches": self.identity(sid)}, sid)
            self.audit()
        print("Role reads and cross-record history completed")

    def filter_controls(self):
        sid = "synthetic_tb_001"
        self.browser.get(self.detail_url(sid))
        gene = self.expected[sid]["rows"][0]["reference_sequence"]
        field = self.browser.find_element(By.CSS_SELECTOR, 'input[aria-label="Select gene"]')
        field.send_keys(gene)
        self.wait.until(lambda _: self.browser.find_elements(By.CSS_SELECTOR, '.choices__item--choice.is-highlighted'))
        field.send_keys(Keys.RETURN)
        old = self.browser.find_element(By.TAG_NAME, "body")
        self.click(self.button("Filter variants"))
        self.wait.until(EC.staleness_of(old))
        expected_ids = sorted(str(r["id"]) for r in self.expected[sid]["rows"] if r["reference_sequence"] == gene)
        self.log("gene-picker-filter", self.identity(sid) and sorted(self.row_ids()) == expected_ids,
            "The visible picker restricts rows to the selected saved identifier", {"rows": len(self.row_ids()), "expected_rows": len(expected_ids)}, sid, screenshot=True)
        self.click(self.browser.find_element(By.LINK_TEXT, "Reset"))
        self.log("filter-reset-restores-rows", sorted(self.row_ids()) == sorted(str(r["id"]) for r in self.expected[sid]["rows"]),
            "The visible Reset action restores every original row", {"rows": len(self.row_ids())}, sid)
        self.apply_filter(sid, {"min-frequency": 100, "min-depth": 1})
        retained = self.browser.find_element(By.NAME, "min-frequency").get_attribute("value") == "100" and self.browser.find_element(By.NAME, "min-depth").get_attribute("value") == "1"
        self.log("filter-input-state-retained", retained, "Submitted display-filter values remain visible", {"values_retained": retained}, sid)
        self.click(self.browser.find_element(By.LINK_TEXT, "Reset"))
        field = self.browser.find_element(By.NAME, "min-frequency")
        field.send_keys("101")
        old = self.browser.find_element(By.TAG_NAME, "body")
        self.click(self.button("Filter variants"))
        invalid = self.browser.execute_script('return arguments[0].validity.rangeOverflow && !!arguments[0].validationMessage', field)
        self.log("filter-native-validation", invalid and old == self.browser.find_element(By.TAG_NAME, "body"),
            "An out-of-range display-filter value receives native validation before submission", {"validation_shown": invalid}, sid)
        self.audit()
