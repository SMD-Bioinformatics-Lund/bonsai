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
from selenium.webdriver.support.ui import WebDriverWait


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--run-dir", type=Path, required=True)
parser.add_argument("--role", default="user_one")
parser.add_argument("--url", default="http://localhost:18000")
args = parser.parse_args()
output = args.run_dir.resolve() / "browser-results" / args.role
output.mkdir(parents=True, exist_ok=True)
options = webdriver.ChromeOptions()
options.binary_location = "/snap/chromium/current/usr/lib/chromium-browser/chrome"
options.add_argument("--headless=new")
options.add_argument("--window-size=1440,1100")
options.add_argument(f"--user-data-dir={output / 'profile'}")
options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
options.add_experimental_option("prefs", {"download.default_directory": str(output / "downloads"),
                                          "download.prompt_for_download": False})
service = Service("/snap/bin/chromium.chromedriver", log_output=str(output / "chromedriver.log"))
browser = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(browser, 20)


def snap():
    """Observe the rendered page and visible controls before choosing an action."""
    state = {"url": browser.current_url, "title": browser.title,
             "text": browser.find_element(By.TAG_NAME, "body").text[:12000], "controls": []}
    for element in browser.find_elements(By.CSS_SELECTOR, "a,button,input,select,textarea"):
        if element.is_displayed():
            state["controls"].append({"tag": element.tag_name, "text": element.text[:120],
                                      "id": element.get_attribute("id"), "name": element.get_attribute("name"),
                                      "type": element.get_attribute("type"), "href": element.get_attribute("href"),
                                      "aria_label": element.get_attribute("aria-label"), "enabled": element.is_enabled()})
    print(json.dumps(state, ensure_ascii=False))


def evidence(name):
    """Save screenshot, DOM and browser console messages for one observed state."""
    if not name.replace("-", "").replace("_", "").isalnum():
        raise ValueError("Use an alphanumeric evidence name")
    browser.save_screenshot(str(output / f"{name}.png"))
    (output / f"{name}.html").write_text(browser.page_source, encoding="utf-8")
    (output / f"{name}.console.json").write_text(json.dumps(browser.get_log("browser"), indent=2))
    print(output / f"{name}.png")


def record(case, status, expected, observed, sample=None, artifact=None):
    if status not in {"PASS", "FAIL", "BLOCKED", "N/A"}:
        raise ValueError("Use an explicit test result")
    item = {"time": datetime.now(timezone.utc).isoformat(), "role": args.role,
            "case": case, "status": status, "expected": expected, "observed": observed,
            "sample": sample, "url": browser.current_url, "artifact": artifact}
    with (args.run_dir / "ui-results.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item) + "\n")
    print(json.dumps(item))


browser.get(args.url)
snap()
