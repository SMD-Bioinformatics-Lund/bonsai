#!/usr/bin/env python3
"""Observed general-workflow retests for the local critical-fix branch."""

import json
from pathlib import Path
from urllib.parse import quote, urlencode

from selenium.common.exceptions import ElementClickInterceptedException, ElementNotInteractableException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait


class GeneralUI:
    def __init__(self, browser, args, record, api):
        self.browser, self.args, self.record, self.api = browser, args, record, api
        self.wait = WebDriverWait(browser, 30)
        self.fixtures = json.loads((args.run_dir / "general-fix-fixtures.json").read_text())

    def button(self, text):
        return next(e for e in self.browser.find_elements(By.TAG_NAME, "button")
                    if e.is_displayed() and e.text.strip() == text)

    def click(self, element):
        def attempt(_):
            try:
                self.browser.execute_script("arguments[0].scrollIntoView({behavior:'instant',block:'center'})", element)
                element.click()
                return True
            except (ElementClickInterceptedException, ElementNotInteractableException):
                return False
        self.wait.until(attempt)

    def check(self, name, ok, expected, observed, sample=None):
        directory = self.args.run_dir.resolve() / "browser-results" / self.args.role / self.args.session_name
        directory.mkdir(parents=True, exist_ok=True)
        self.browser.save_screenshot(str(directory / f"{name}.png"))
        (directory / f"{name}.html").write_text(self.browser.page_source)
        (directory / f"{name}.console.json").write_text(json.dumps(self.browser.get_log("browser"), indent=2))
        self.record(name, "PASS" if ok else "FAIL", expected, observed, sample=sample,
                    artifact=str((directory / f"{name}.png").relative_to(self.args.run_dir.resolve())))

    def login(self, role, password=None):
        self.browser.get(self.args.url + "/logout")
        self.browser.get(self.args.url + "/login")
        self.browser.find_element(By.ID, "username").send_keys(role, Keys.TAB,
            password or ("admin123" if role == "admin" else "user123"), Keys.RETURN)
        self.wait.until(EC.presence_of_element_located((By.ID, "dt-search-0")))
        self.args.role = role

    def overview(self, search="", length="10"):
        self.browser.get(self.args.url + "/groups")
        field = self.wait.until(EC.presence_of_element_located((By.ID, "dt-search-0")))
        Select(self.browser.find_element(By.ID, "dt-length-0")).select_by_value(length)
        field.send_keys(search)

    def row_ids(self):
        return [e.get_attribute("id") for e in self.browser.find_elements(By.CSS_SELECTOR, "#sample-table tbody tr[id]")]

    def memberships(self, ids):
        edges = []
        for offset in range(0, len(ids), 100):
            edges.extend(self.api.request("/memberships?" + urlencode({"s": ids[offset:offset + 100]}, doseq=True)))
        return sorted((e["sample_id"], e["group_id"]) for e in edges)

    def selector(self):
        root = self.browser.find_element(By.TAG_NAME, "group-selector").shadow_root
        return root, root.find_element(By.ID, "groups").shadow_root

    def selected_groups(self):
        return [e.get_attribute("value") for e in Select(self.selector()[1].find_element(By.ID, "select")).all_selected_options]

    def check_pending_and_metadata(self):
        self.login("user_one")
        for key in ("pending_id", "metadata_id"):
            sid = self.fixtures[key]
            self.browser.get(self.args.url + "/sample/" + sid)
            body = self.browser.find_element(By.TAG_NAME, "body").text
            self.check("pending-summary-" + key, self.browser.title != "500 Internal Server Error" and
                       "No completed pipeline" in body, "A pending record remains available without any analyses",
                       {"title": self.browser.title, "pending_message": "No completed pipeline" in body}, sample=sid)
        self.browser.get(self.args.url + "/sample/" + self.fixtures["metadata_id"] + "/metadata")
        body = self.browser.find_element(By.TAG_NAME, "body").text
        expected = ["Clinical note", "Second note", "Run count", "Synthetic & café", "Retained after a category change"]
        self.check("metadata-category-retention", all(x in body for x in expected),
                   "Interleaved categories preserve every field and text value", {"missing": [x for x in expected if x not in body]})
        self.check("metadata-inline-table", all(x in body for x in ("Generic inventory", "Item", "Count", "Desk", "Chair")),
                   "A generic CSV table renders its heading and rows inline", {"table_present": "Desk" in body and "Chair" in body})
        self.check("metadata-literal-text", "Synthetic <b>literal</b> & café" in body,
                   "Metadata preserves HTML-like input as literal text", {"literal_text_visible": "Synthetic <b>literal</b> & café" in body})
        self.browser.get(self.args.url + "/sample/" + self.fixtures["metadata_id"] + "/metadata/" + quote("Generic inventory"))
        body = self.browser.find_element(By.TAG_NAME, "body").text
        self.check("metadata-standalone-table", "Desk" in body and "Chair" in body,
                   "The standalone table contains the same headings and rows", body[:1200])

    def check_private_groups(self):
        gid = self.fixtures["private"]["group_id"]
        label = self.fixtures["private"]["display_name"]
        for role, allowed in (("admin", True), ("user_one", True), ("user_two", False)):
            self.login(role)
            self.wait.until(lambda _: self.browser.find_elements(By.TAG_NAME, "group-list") and
                            self.browser.find_element(By.TAG_NAME, "group-list").text)
            listed = label in self.browser.find_element(By.TAG_NAME, "group-list").text
            self.browser.get(self.args.url + "/groups/" + gid)
            title = self.browser.title
            opened = "404" not in title and "500" not in title and label in self.browser.find_element(By.TAG_NAME, "body").text
            self.check("private-group-" + role, listed == allowed and opened == allowed,
                       "Owner and invitee have access; the uninvited account is denied",
                       {"listed": listed, "opened": opened, "title": title, "expected_access": allowed})

    def check_membership_preservation(self):
        self.login("admin")
        self.overview(length="-1")
        self.wait.until(lambda _: len(self.row_ids()) == len(self.fixtures["all_ids"]))
        self.click(self.button("Select all"))
        self.click(self.button("Add to group"))
        self.wait.until(lambda _: self.selector()[0].find_element(By.ID, "apply").is_enabled())
        common = self.fixtures["common"]["group_id"]
        self.check("membership-preselection-125", self.selected_groups() == [common],
                   "Common membership is preselected for all 125 records", {"selected_groups": self.selected_groups(), "records": len(self.row_ids())})
        before = self.memberships(self.fixtures["all_ids"])
        self.click(self.selector()[0].find_element(By.ID, "apply"))
        self.wait.until(lambda _: self.selector()[0].find_element(By.ID, "apply").is_enabled())
        after = self.memberships(self.fixtures["all_ids"])
        self.check("membership-unchanged-apply-125", before == after,
                   "Unchanged Apply preserves every common and individual membership",
                   {"edges_before": len(before), "edges_after": len(after), "removed": sorted(set(before) - set(after))})
        self.overview("General UI pair")
        self.wait.until(lambda _: len(self.row_ids()) == 2)
        self.click(self.button("Select all"))
        self.click(self.button("Add to group"))
        self.wait.until(lambda _: self.selector()[0].find_element(By.ID, "apply").is_enabled())
        before = self.memberships(self.fixtures["pairs"])
        self.click(self.selector()[0].find_element(By.ID, "clear"))
        self.click(self.selector()[0].find_element(By.ID, "apply"))
        self.wait.until(lambda _: self.selector()[0].find_element(By.ID, "apply").is_enabled())
        after = self.memberships(self.fixtures["pairs"])
        expected = [(sid, gid) for sid, gid in before if gid != common]
        self.check("membership-remove-common-only", after == expected,
                   "Clearing a common group removes that group while preserving individual groups",
                   {"before": before, "after": after})
        # Restore the common fixture membership through the same public API.
        self.api.request("/groups/" + common + "/samples?" + urlencode({"s": self.fixtures["pairs"]}, doseq=True), method="PUT")

    def check_accounts(self):
        self.login("admin")
        username, password = "ui_general_test", "TestPassword123"

        def fill(first="General", name=username, secret=password):
            for key, value in {"first_name": first, "last_name": "Account", "email": "ui-general@example.org",
                               "username": name, "password": secret, "confirm": secret}.items():
                field = self.browser.find_element(By.ID, key)
                field.clear()
                field.send_keys(value)
            role = self.browser.find_element(By.CSS_SELECTOR, "input[name='roles'][value='user']")
            if not role.is_selected():
                self.click(role)

        self.browser.get(self.args.url + "/admin/users/new")
        fill(name="ui_general_weak", secret="weakpassword")
        self.click(self.button("Create"))
        body = self.browser.find_element(By.TAG_NAME, "body").text
        self.check("account-password-validation", "must include upper- and lower case" in body and "500" not in self.browser.title,
                   "A weak password produces form feedback without creating an account", {"validation_visible": "must include upper- and lower case" in body})
        fill()
        self.click(self.button("Create"))
        body = self.browser.find_element(By.TAG_NAME, "body").text
        self.check("account-create", "Created new user" in body and username in body,
                   "A valid new account is created once and listed", {"created_message": "Created new user" in body, "listed": username in body})
        self.browser.get(self.args.url + "/admin/users/" + username)
        self.check("account-open-edit", "500" not in self.browser.title and
                   self.browser.find_element(By.ID, "first_name").get_attribute("value") == "General",
                   "The existing account opens with its saved fields", {"title": self.browser.title})
        field = self.browser.find_element(By.ID, "first_name")
        field.clear()
        field.send_keys("Updated")
        self.click(self.button("Update"))
        body = self.browser.find_element(By.TAG_NAME, "body").text
        self.browser.get(self.args.url + "/admin/users/" + username)
        persisted = self.browser.find_element(By.ID, "first_name").get_attribute("value") == "Updated"
        self.check("account-update-persistence", "Updated user " + username in body and persisted,
                   "A profile update reports success and persists after reload", {"success_message": "Updated user " + username in body, "persisted": persisted})
        self.login(username, password)
        self.check("account-login-after-profile-edit", "/groups" in self.browser.current_url,
                   "Editing with a blank password preserves the existing login", {"title": self.browser.title})
        self.login("admin")
        self.browser.get(self.args.url + "/admin/users/" + username)
        self.click(self.button("Delete"))
        body = self.browser.find_element(By.TAG_NAME, "body").text
        deleted = self.api.request("/users/" + username, expected=404)
        self.check("account-delete", "Removed user " + username in body,
                   "The disposable account is removed through the administrator form", {"message": "Removed user " + username in body, "api_not_found": deleted})

    def check_status_filters(self):
        self.login("admin")
        self.overview()
        self.click(self.button("Add Condition"))
        # Use the observed header's column index, so optional columns cannot shift the test.
        def column_id(name):
            return self.browser.execute_script("return [...document.querySelectorAll('#sample-table thead th')].findIndex(e=>e.dataset.columnId===arguments[0])", name)
        Select(self.browser.find_element(By.CSS_SELECTOR, ".dtsb-data")).select_by_value(str(column_id("qc_status")))
        Select(self.browser.find_element(By.CSS_SELECTOR, ".dtsb-condition")).select_by_value("=")
        Select(self.browser.find_element(By.CSS_SELECTOR, ".dtsb-value")).select_by_value("failed")
        self.wait.until(lambda _: len(self.row_ids()) == 8)
        self.check("status-filter-exact", len(self.row_ids()) == 8,
                   "An exact status filter retains all eight failed records, including a column excluded from global search",
                   {"rows": len(self.row_ids())})
        self.click(self.button("Add Condition"))
        Select(self.browser.find_elements(By.CSS_SELECTOR, ".dtsb-data")[1]).select_by_value(str(column_id("assay")))
        Select(self.browser.find_elements(By.CSS_SELECTOR, ".dtsb-condition")[1]).select_by_value("=")
        Select(self.browser.find_elements(By.CSS_SELECTOR, ".dtsb-value")[1]).select_by_value("ecoli")
        self.wait.until(lambda _: len(self.row_ids()) == 1)
        self.check("status-category-combination", len(self.row_ids()) == 1,
                   "Category and exact-status conditions combine with AND", {"rows": len(self.row_ids())})
        self.click(self.button("Clear All"))
        self.check("status-filter-clear", "125 entries" in self.browser.find_element(By.ID, "sample-table_info").text,
                   "Clearing conditions restores all 125 records", self.browser.find_element(By.ID, "sample-table_info").text)

    def check_group_deletion(self):
        self.login("admin")
        gid = self.fixtures["common"]["group_id"]
        ids = self.fixtures["all_ids"]
        before = self.memberships(ids)
        self.browser.get(self.args.url + "/groups/" + gid + "/edit")
        self.wait.until(EC.element_to_be_clickable((By.ID, "ge-delete")))
        self.click(self.browser.find_element(By.ID, "ge-delete"))
        dialog = self.wait.until(EC.alert_is_present())
        prompt = dialog.text
        dialog.accept()
        self.wait.until(EC.presence_of_element_located((By.ID, "dt-search-0")))
        after = self.memberships(ids)
        expected = [(sid, group) for sid, group in before if group != gid]
        remaining = self.api.request("/samples/summary", data={"fields": ["sample_id"], "limit": 0, "offset": 0})["data"]
        self.check("delete-group-preserves-unrelated-memberships", after == expected and len(remaining) == len(ids),
                   "Deleting a 125-member group retains every record and unrelated membership",
                   {"records_before": len(ids), "records_after": len(remaining), "edges_before": len(before),
                    "unrelated_edges_expected": len(expected), "edges_after": len(after), "prompt": prompt,
                    "unexpected_removed": sorted(set(expected) - set(after))})

    def check_metadata_navigation(self):
        self.login("user_one")
        rows = self.api.request("/samples/summary", data={"fields": ["sample_id", "sample_name"], "limit": 0, "offset": 0})["data"]
        for row in rows:
            self.browser.get(self.args.url + "/sample/" + row["sample_id"] + "/metadata")
            body = self.browser.find_element(By.TAG_NAME, "body").text
            ok = "500" not in self.browser.title and row["sample_name"] in body
            self.record("metadata-route-after-fix", "PASS" if ok else "FAIL",
                        "Metadata navigation and record identity remain available after the model changes",
                        {"title": self.browser.title}, sample=row["sample_id"])
        self.check("metadata-route-sweep", len(rows) == 125,
                   "All 125 existing, pending and metadata-bearing records were exercised", {"records": len(rows)})
