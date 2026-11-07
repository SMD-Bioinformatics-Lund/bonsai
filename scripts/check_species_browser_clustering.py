"""Exercise each prepared clustering combination through the observed basket UI.

Call run_suite from species_browser_session.py's interactive Python prompt.
The supplied record/evidence callbacks keep baseline and fix runs separate.
"""

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import ElementClickInterceptedException, ElementNotInteractableException
from selenium.webdriver.support.ui import Select, WebDriverWait


def run_suite(browser, run_dir, output, record, evidence, base_url, *, run_label):
    root, output = Path(run_dir).resolve(), Path(output).resolve()
    cases = json.loads((root / "fixtures/expectations.json").read_text())["samples"]
    api_cases = json.loads((root / "species-clustering-results.json").read_text())["results"]
    labels = {"minhash": "MinHash", "ska": "SNV", "mlst": "MLST", "cgmlst": "cgMLST"}
    wait = WebDriverWait(browser, 45)
    # The browser profile's download directory stays fixed when the account changes.
    download_root = root / "browser-results/user_one" / run_label / "downloads"
    results = []

    def click(element):
        def attempt(_driver):
            try:
                browser.execute_script("arguments[0].scrollIntoView({behavior:'instant',block:'center'})", element)
                element.click()
                return True
            except (ElementClickInterceptedException, ElementNotInteractableException):
                # Bootstrap offcanvas and tree panels animate before becoming clickable.
                return False
        wait.until(attempt)

    def button(text, selector="button"):
        return next(e for e in browser.find_elements(By.CSS_SELECTOR, selector)
                    if e.is_displayed() and e.text.strip() == text)

    def basket_ids():
        return [e.get_attribute("href").rsplit("/", 1)[-1]
                for e in browser.find_elements(By.CSS_SELECTOR, '#basket-content a[href*="/sample/"]')]

    def save_progress():
        (root / f"{run_label}-browser-clustering-results.json").write_text(json.dumps({
            "time": datetime.now(timezone.utc).isoformat(), "phase": run_label,
            "scope": "Browser selection, job completion, name rendering and exact exported leaf IDs",
            "results": results,
        }, indent=2) + "\n")

    for assay in dict.fromkeys(item["assay"] for item in api_cases):
        assay_cases = [case for case in cases if case["assay"] == assay and not case["sample_id"].endswith("_010")]
        prefix = assay_cases[0]["sample_id"].rsplit("_", 1)[0] + "_00"
        browser.get(base_url.rstrip("/") + "/groups")
        field = wait.until(lambda d: d.find_element(By.ID, "dt-search-0"))
        field.send_keys(prefix)
        wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, "#sample-table tbody tr[id]")) == 9)
        click(browser.find_element(By.ID, "open-basket-btn"))
        click(browser.find_element(By.ID, "clear-basket-btn"))
        click(browser.find_element(By.ID, "close-basket-btn"))
        wait.until(lambda d: not d.find_element(By.ID, "basket-offcanvas").is_displayed())
        click(button("Select all"))
        click(browser.find_element(By.ID, "add-to-basket-btn"))
        click(browser.find_element(By.ID, "open-basket-btn"))
        wait.until(lambda d: len(basket_ids()) == 9)
        selected = basket_ids()
        main_window = browser.current_window_handle
        for api_case in (item for item in api_cases if item["assay"] == assay):
            method = api_case["method"]
            result = {"assay": assay, "method": method, "selected_ids": selected}
            name = f"cluster-{assay}-{method}"
            try:
                next(e for e in browser.find_elements(By.CSS_SELECTOR, "#basket-offcanvas button")
                     if "Cluster" in e.text).send_keys(Keys.RETURN)
                wait.until(lambda d: any(e.is_displayed() and e.text.strip() == labels[method]
                                        for e in d.find_elements(By.CSS_SELECTOR, "#basket-offcanvas a")))
                next(e for e in browser.find_elements(By.CSS_SELECTOR, "#basket-offcanvas a")
                     if e.is_displayed() and e.text.strip() == labels[method]).send_keys(Keys.RETURN)
                wait.until(lambda d: len(d.window_handles) > 1)
                browser.switch_to.window(browser.window_handles[-1])
                wait.until(lambda d: d.find_elements(By.ID, "save-tree-nwk"))
                click(browser.find_element(By.ID, "tree-menu"))
                wait.until(lambda d: d.find_element(By.ID, "mst-node-menu").is_displayed())
                click(browser.find_element(By.ID, "mst-node-menu"))
                wait.until(lambda d: d.find_element(By.ID, "show-node-labels").is_displayed())
                check = browser.find_element(By.ID, "show-node-labels")
                if not check.is_selected():
                    click(check)
                Select(browser.find_element(By.ID, "node-label-text")).select_by_visible_text("Name")
                names = browser.execute_script("return [...document.querySelectorAll('svg text')].map(e=>e.textContent).join(' ')")
                missing = [case["sample_name"] for case in assay_cases if case["sample_name"] not in names]
                click(browser.find_element(By.ID, "save-tree-nwk"))
                field = wait.until(lambda d: d.find_element(By.ID, "filename"))
                filename = f"{run_label}-{assay}-{method}.nwk"
                field.clear()
                field.send_keys(filename)
                click(button("Save", ".ui-dialog button"))
                destination = download_root / filename
                wait.until(lambda d: destination.is_file() and destination.stat().st_size > 0)
                leaves = re.findall(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", destination.read_text())
                exact = Counter(leaves) == Counter(selected)
                status = "PASS" if exact and not missing else "FAIL"
                evidence(name)
                artifact = str((output / f"{name}.png").relative_to(root))
                observed = {"missing_names": missing, "leaf_count": len(leaves), "exact_ids": exact,
                            "download": str(destination.relative_to(root))}
                record(name, status, "Nine selected names render and each selected ID occurs once in the downloaded tree",
                       observed, sample=assay, artifact=artifact)
                result.update(status=status, **observed, artifact=artifact)
            except Exception as error:
                result.update(status="BLOCKED", error=f"{type(error).__name__}: {str(error).split('Stacktrace:')[0]}"[:600])
                record(name, "BLOCKED", "Browser can complete this clustering workflow", result["error"], sample=assay)
            finally:
                if browser.current_window_handle != main_window:
                    browser.close()
                    browser.switch_to.window(main_window)
            results.append(result)
            save_progress()
            print(f"BROWSER CLUSTER {len(results)}/28 {assay}/{method}: {result['status']}", flush=True)
        click(browser.find_element(By.ID, "clear-basket-btn"))
        click(browser.find_element(By.ID, "close-basket-btn"))
        wait.until(lambda d: not d.find_element(By.ID, "basket-offcanvas").is_displayed())
    return results
