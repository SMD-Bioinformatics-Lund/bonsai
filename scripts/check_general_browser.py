#!/usr/bin/env python3
"""Exercise general UI controls without running or interpreting analyses.

Called from species_browser_session.py's persistent Selenium prompt. All data
changes in this module are browser selection state and authentication state.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait


def run_suite(browser, record, evidence, args, output):
    wait = WebDriverWait(browser, 25)

    def button(label):
        return next(e for e in browser.find_elements(By.TAG_NAME, "button")
                    if e.is_displayed() and e.text.strip() == label)

    def click(element):
        browser.execute_script("arguments[0].scrollIntoView({behavior:'instant',block:'center'})", element)
        element.click()

    def check(name, ok, expected, observed):
        evidence(name)
        record(name, "PASS" if ok else "FAIL", expected, observed,
               artifact=str((output / f"{name}.png").relative_to(args.run_dir.resolve())))

    browser.set_window_size(1440, 1100)
    browser.get(args.url + "/groups")
    field = wait.until(EC.presence_of_element_located((By.ID, "dt-search-0")))
    Select(browser.find_element(By.ID, "dt-length-0")).select_by_value("10")
    field.send_keys("synthetic_sa_")
    wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, "#sample-table tbody tr[id]")) == 10)
    click(button("Select all"))
    click(button("Show only selected"))
    click(button("Deselect all"))
    # A DOM snapshot on the next frame avoids confusing asynchronous paint with a stale table.
    browser.execute_async_script("const done=arguments[0];requestAnimationFrame(()=>requestAnimationFrame(done));")
    state = browser.execute_script("""
      return {rows:document.querySelectorAll('#sample-table tbody tr[id]').length,
              selected:document.querySelectorAll('#sample-table tbody tr.selected').length,
              info:document.querySelector('#sample-table_info').innerText};
    """)
    check("deselect-all-with-selected-filter", state["rows"] == 0 and state["selected"] == 0,
          "Clearing selection while Show only selected is active leaves no result rows", state)

    for width in (390, 320):
        browser.set_window_size(width, 844)
        browser.get(args.url + "/groups")
        wait.until(EC.presence_of_element_located((By.ID, "dt-search-0")))
        dimensions = browser.execute_script("""
          const root=document.documentElement;
          return {viewport:innerWidth, page:root.scrollWidth,
            overflowing:[...document.querySelectorAll('body *')].filter(e=>e.getClientRects().length &&
              e.getBoundingClientRect().right>innerWidth+2 && getComputedStyle(e).position!=='fixed')
              .slice(0,8).map(e=>({tag:e.tagName,id:e.id,class:e.className}))};
        """)
        check(f"overview-mobile-{width}", dimensions["page"] <= dimensions["viewport"] + 2,
              "The overview fits the narrow viewport with table scrolling contained", dimensions)

    browser.set_window_size(1440, 1100)
    browser.get(args.url + "/admin/users")
    check("nonadmin-admin-denial", browser.title != "500 Internal Server Error" and
          "Manage users" not in browser.find_element(By.TAG_NAME, "body").text,
          "Administrative navigation is denied without a server error", {"title": browser.title})
    browser.get(args.url + "/logout")
    browser.get(args.url + "/groups")
    check("logout-protected-navigation", "/login" in browser.current_url,
          "Protected navigation after logout returns to login", {"url": browser.current_url})
    browser.find_element(By.ID, "username").send_keys("user_one", Keys.TAB, "incorrect-password", Keys.RETURN)
    body = browser.find_element(By.TAG_NAME, "body").text
    check("invalid-password-feedback", "/login" in browser.current_url and "500" not in browser.title,
          "An incorrect password keeps the login form available and provides feedback", body)
    browser.find_element(By.ID, "username").clear()
    browser.find_element(By.ID, "username").send_keys("user_one", Keys.TAB, "user123", Keys.RETURN)
    wait.until(EC.presence_of_element_located((By.ID, "dt-search-0")))
    check("keyboard-login", "/groups" in browser.current_url,
          "The username, password and submit flow works with Tab and Return", {"title": browser.title})
