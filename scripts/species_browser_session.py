#!/usr/bin/env python3
"""Start a persistent Selenium session for an observed, interactive UI pass.

Run with Python -i. The browser, snap(), evidence() and record() remain available
at the prompt. All output files are operational test evidence on the data drive.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--run-dir", type=Path, required=True)
parser.add_argument("--role", default="user_one")
parser.add_argument("--session-name", default="")
parser.add_argument("--results-file", default="ui-results.jsonl")
parser.add_argument("--phase", default="initial")
parser.add_argument("--performance-log", action="store_true")
parser.add_argument("--url", default="http://localhost:18000")
args = parser.parse_args()
output = args.run_dir.resolve() / "browser-results" / args.role
if args.session_name:
    output = output / args.session_name
output.mkdir(parents=True, exist_ok=True)
options = webdriver.ChromeOptions()
options.binary_location = "/snap/chromium/current/usr/lib/chromium-browser/chrome"
options.add_argument("--headless=new")
options.add_argument("--window-size=1440,1100")
options.add_argument(f"--user-data-dir={output / 'profile'}")
options.set_capability("goog:loggingPrefs", {"browser": "ALL", **({"performance": "ALL"} if args.performance_log else {})})
options.add_experimental_option("prefs", {"download.default_directory": str(output / "downloads"),
                                          "download.prompt_for_download": False,
                                          "net.network_prediction_options": 2})
service = Service("/snap/bin/chromium.chromedriver", log_output=str(output / "chromedriver.log"))
browser = webdriver.Chrome(service=service, options=options)
browser.set_page_load_timeout(45)
wait = WebDriverWait(browser, 20)


def snap(limit=6000):
    """Observe the rendered page and visible controls before choosing an action."""
    state = browser.execute_script("""
        const controls = [...document.querySelectorAll('a,button,input,select,textarea')]
            .filter(e => e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden')
            .map(e => ({tag:e.tagName.toLowerCase(), text:(e.innerText||'').slice(0,120),
                id:e.id, name:e.getAttribute('name'), type:e.getAttribute('type'), href:e.href||null,
                aria_label:e.getAttribute('aria-label'), enabled:!e.matches(':disabled')}));
        return {url:location.href, title:document.title,
            text:document.body.innerText.slice(0,arguments[0]), controls};
    """, limit)
    print(json.dumps(state, ensure_ascii=False))


def evidence(name):
    """Save screenshot, DOM and browser console messages for one observed state."""
    if not name.replace("-", "").replace("_", "").isalnum():
        raise ValueError("Use an alphanumeric evidence name")
    browser.save_screenshot(str(output / f"{name}.png"))
    (output / f"{name}.html").write_text(browser.page_source, encoding="utf-8")
    (output / f"{name}.console.json").write_text(json.dumps(browser.get_log("browser"), indent=2))
    print(output / f"{name}.png")


def record(case, status, expected, observed, sample=None, artifact=None, observed_url=None):
    if status not in {"PASS", "FAIL", "BLOCKED", "N/A"}:
        raise ValueError("Use an explicit test result")
    item = {"time": datetime.now(timezone.utc).isoformat(), "role": args.role,
            "phase": args.phase,
            "case": case, "status": status, "expected": expected, "observed": observed,
            "sample": sample, "url": observed_url or browser.current_url, "artifact": artifact}
    with (args.run_dir / args.results_file).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item) + "\n")
    print(json.dumps(item))


def open_sample_by_id(sid, text_limit=6500):
    """Follow the visible overview search and Open link using keyboard activation."""
    cases = json.loads((args.run_dir / "fixtures/expectations.json").read_text())["samples"]
    case = next(item for item in cases if item["sample_id"] == sid)
    browser.get(args.url.rstrip("/") + "/groups")
    field = wait.until(lambda driver: driver.find_element(By.ID, "dt-search-0"))
    field.clear()
    field.send_keys(sid)
    wait.until(lambda driver: len(driver.find_elements(By.CSS_SELECTOR, "tbody tr")) == 1
               and case["sample_name"] in driver.find_element(By.CSS_SELECTOR, "tbody tr").text)
    browser.find_element(By.LINK_TEXT, "Open").send_keys(Keys.RETURN)
    body = browser.find_element(By.TAG_NAME, "body").text
    status = "PASS" if (browser.title != "500 Internal Server Error"
                        and case["sample_name"] in body and case["species"] in body) else "FAIL"
    evidence(sid + "-detail")
    artifact = str((output / f"{sid}-detail.png").relative_to(args.run_dir.resolve()))
    record("sample-detail-navigation", status, "Expected sample identity and species render",
           browser.title, sample=sid, artifact=artifact)
    state = {"sample": sid, "title": browser.title, "url": browser.current_url,
             "artifact": artifact, "body": body[:text_limit]}
    print(json.dumps(state))
    return state


browser.get(args.url)
snap()
