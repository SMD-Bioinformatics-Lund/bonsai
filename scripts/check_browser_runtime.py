#!/usr/bin/env python3
"""Verify the approved local Chromium/Selenium route before testing Bonsai."""

import argparse
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    options = webdriver.ChromeOptions()
    options.binary_location = "/snap/chromium/current/usr/lib/chromium-browser/chrome"
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,1000")
    options.add_argument(f"--user-data-dir={args.output.resolve() / 'profile'}")
    service = Service("/snap/bin/chromium.chromedriver", log_output=str(args.output / "chromedriver.log"))
    with webdriver.Chrome(service=service, options=options) as browser:
        browser.get("data:text/html,<title>Browser preflight</title><button onclick=\"this.textContent='Clicked'\">Ready</button>")
        browser.find_element(By.TAG_NAME, "button").click()
        WebDriverWait(browser, 10).until(lambda driver: driver.find_element(By.TAG_NAME, "button").text == "Clicked")
        browser.save_screenshot(str(args.output / "preflight.png"))
        print(f"PASS Chromium {browser.capabilities['browserVersion']}: navigation, visible control, click and screenshot")


if __name__ == "__main__":
    main()
