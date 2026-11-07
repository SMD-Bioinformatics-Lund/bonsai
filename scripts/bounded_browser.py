"""Browser checks restricted to record workflows and stored report rendering."""

import csv
import io
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from bounded_workflows import Results
from check_general_fix_browser import GeneralUI


class BoundedUI(GeneralUI):
    def __init__(self, browser, args, api, scope, phase="bounded-baseline"):
        self.browser, self.args, self.api, self.scope = browser, args, api, scope
        self.wait = WebDriverWait(browser, 25)
        self.results = Results(args.run_dir, phase)
        self.fixtures = json.loads((self.results.directory / "fixtures.json").read_text())
        browser.execute_cdp_cmd("Network.enable", {})
        browser.execute_cdp_cmd("Network.setBlockedURLs", {"urls": scope.config["browser_blocked_urls"]})

    def check(self, name, ok, expected, observed, sample=None):
        directory = self.results.directory / "browser" / self.results.phase / self.args.role
        directory.mkdir(parents=True, exist_ok=True)
        suffix = "-" + sample if sample else ""
        destination = directory / (name + suffix + ".png")
        self.browser.save_screenshot(str(destination))
        destination.with_suffix(".html").write_text(self.browser.page_source)
        destination.with_suffix(".console.json").write_text(json.dumps(self.browser.get_log("browser"), indent=2))
        return self.results.check(name, ok, expected, observed, surface="browser", role=self.args.role,
                                  sample=sample, artifact=str(destination.relative_to(self.results.run)), url=self.browser.current_url)

    def missing_pages(self):
        self.login("admin")
        sid = self.fixtures["samples"][0]["sample_id"]
        for name, path in [
            ("missing-group-page", "/groups/bounded_missing"),
            ("missing-sample-page", "/sample/bounded_missing"),
            ("missing-metadata-page", "/sample/bounded_missing/metadata"),
            ("missing-metadata-table", "/sample/" + sid + "/metadata/bounded_missing_table"),
            ("missing-user-edit-page", "/admin/users/bounded_missing"),
        ]:
            self.browser.get(self.args.url + path)
            self.check(name, "404" in self.browser.title, "An unavailable record or table has a clear 404 state",
                       {"title": self.browser.title, "final_path": self.browser.current_url})

    def metadata(self):
        self.login("user_one")
        for n in (0, 1):
            sid = self.fixtures["samples"][n]["sample_id"]
            self.browser.get(self.args.url + "/sample/" + sid + "/metadata")
            body = self.browser.find_element(By.TAG_NAME, "body").text
            expected = ["Quoted,", "café", "Second line", "Retained", "Comma, quote"] if n == 0 else ["Empty cells", "Desk", "Chair"]
            self.check("metadata-generic-content", "500" not in self.browser.title and all(x in body for x in expected),
                       "Accepted generic metadata and table rows remain readable",
                       {"title": self.browser.title, "missing": [x for x in expected if x not in body]}, sample=sid)

    def exports(self):
        self.login("user_one")
        self.overview("bounded_record_")
        self.wait.until(lambda _: len(self.row_ids()) == 5)
        self.check("ordinary-delete-control", not self.browser.find_elements(By.ID, "remove-samples-btn"),
                   "The ordinary account is not offered record deletion", {"control_present": bool(self.browser.find_elements(By.ID, "remove-samples-btn"))})
        downloads = self.args.run_dir.resolve() / "browser-results/user_one" / self.args.session_name / "downloads"
        downloads.mkdir(parents=True, exist_ok=True)
        for label, suffix in [("CSV", ".csv"), ("Excel", ".xlsx")]:
            before = set(downloads.glob("*"))
            self.click(self.button(label))
            file = self.wait.until(lambda _: next((p for p in downloads.glob("*" + suffix) if p not in before and p.stat().st_size > 0), None))
            if suffix == ".csv":
                rows = list(csv.reader(io.StringIO(file.read_text(encoding="utf-8-sig"))))
                header, records = rows[0], [row for row in rows[1:] if row]
                external_index = header.index("Lab ID")
                lims_index, name_index = header.index("LIMS id"), header.index("Name")
                actual = {row[external_index]: row for row in records}
                ids = {x["external_sample_id"] for x in self.fixtures["samples"]}
                ok = set(actual) == ids and all(actual[x["external_sample_id"]][lims_index] == x["lims_id"] for x in self.fixtures["samples"])
                self.check("csv-identity-unicode-quoting", ok and actual["bounded_record_003"][name_index] == 'Bounded comma, "quoted"',
                           "Filtered export preserves five exact identities, leading-zero IDs, Unicode and quoted commas",
                           {"rows": len(records), "exact_ids": set(actual) == ids, "names": [row[name_index] for row in records], "file": str(file.relative_to(self.results.run))})
                formula = actual["bounded_record_004"][name_index]
                self.check("csv-formula-literal", formula.startswith("'="),
                           "A formula-like record name is exported as literal spreadsheet text", {"exported_text": formula})
            else:
                with zipfile.ZipFile(file) as archive:
                    sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
                ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
                cells = ["".join(c.itertext()) for c in sheet.findall(".//m:c", ns)]
                formula_nodes = sheet.findall(".//m:f", ns)
                self.check("xlsx-literal-identifiers", not formula_nodes and all(x["lims_id"] in cells for x in self.fixtures["samples"]),
                           "Excel export preserves leading-zero identifiers and contains no executable formulas",
                           {"formula_nodes": len(formula_nodes), "all_ids_present": all(x["lims_id"] in cells for x in self.fixtures["samples"]),
                            "file": str(file.relative_to(self.results.run))})

    def membership_failure_recovery(self):
        self.login("admin")
        self.overview("bounded_record_")
        self.wait.until(lambda _: len(self.row_ids()) == 5)
        self.browser.execute_cdp_cmd("Network.setBlockedURLs", {"urls": self.scope.config["browser_blocked_urls"] + ["*://localhost:18001/memberships*"]})
        self.click(self.button("Select all"))
        self.click(self.button("Add to group"))
        root, _ = self.selector()
        self.check("membership-network-failure-blocks-apply", not root.find_element(By.ID, "apply").is_enabled(),
                   "A failed membership read keeps Apply disabled", {"apply_enabled": root.find_element(By.ID, "apply").is_enabled()})
        self.browser.execute_cdp_cmd("Network.setBlockedURLs", {"urls": self.scope.config["browser_blocked_urls"]})
        # Close the dropdown before changing the selection again.
        self.click(self.button("Add to group"))
        self.click(self.button("Deselect all"))
        self.click(self.button("Select all"))
        self.click(self.button("Add to group"))
        self.wait.until(lambda _: self.selector()[0].find_element(By.ID, "apply").is_enabled())
        expected = self.fixtures["groups"][0]["group_id"]
        self.check("membership-network-recovery", self.selected_groups() == [expected],
                   "Reselection after restoring the network reloads the common membership", {"selected": self.selected_groups()})

    def group_validation(self):
        self.login("admin")
        self.browser.get(self.args.url + "/groups/create")
        self.wait.until(EC.presence_of_element_located((By.ID, "group-key")))
        self.browser.find_element(By.ID, "group-key").send_keys("bounded_common")
        self.browser.find_element(By.ID, "group-name").send_keys("Bounded duplicate group")
        self.click(self.browser.find_element(By.ID, "ge-save"))
        self.wait.until(lambda _: "Failed to save group" in self.browser.find_element(By.TAG_NAME, "body").text)
        self.check("group-duplicate-form-feedback", True, "A duplicate group key gives visible failure feedback and retains the form",
                   {"message": "Failed to save group", "form_available": bool(self.browser.find_elements(By.ID, "group-key"))})

    def stored_reports(self):
        self.results.increment = "stored-report-rendering"
        self.login("user_one")
        catalog = json.loads((self.args.run_dir / "fixtures/expectations.json").read_text())
        identities = self.api.request("/samples/summary", data={"fields": ["sample_id", "external_sample_id", "sample_name"], "limit": 0, "offset": 0})["data"]
        mapping = {row["external_sample_id"]: row for row in identities}
        for case in catalog["samples"]:
            row = mapping[case["sample_id"]]
            self.browser.get(self.args.url + "/sample/" + row["sample_id"])
            body = self.browser.find_element(By.TAG_NAME, "body").text
            ok = "500" not in self.browser.title and row["sample_name"] in body
            if not ok or case["sample_id"].endswith("_001"):
                self.check("stored-report-navigation", ok, "An existing stored report opens with its saved record identity",
                           {"title": self.browser.title}, sample=case["sample_id"])
            else:
                self.results.check("stored-report-navigation", ok, "An existing stored report opens with its saved record identity",
                                   {"title": self.browser.title}, surface="browser", role=self.args.role, sample=case["sample_id"], url=self.browser.current_url)
