#!/usr/bin/env python3
"""Compare saved-report envelopes with API storage and ordinary browser views."""
import csv
from datetime import datetime, timezone
import json
import urllib.parse
import urllib.request

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from kleborate_saved_report_cases import ROOT, PILOT, CASES, now, hashes, write


def main():
    assert json.loads((ROOT / 'import-status.json').read_text())['status'] == 'COMPLETE'
    account = json.loads((PILOT / 'bonsai/accounts.json').read_text())['pilot_viewer']
    body = urllib.parse.urlencode({'username': account['username'], 'password': account['password']}).encode()
    with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18101/token', data=body), timeout=30) as response:
        token = json.load(response)['access_token']
    def get(sid):
        req = urllib.request.Request('http://127.0.0.1:18101/samples/' + sid, headers={'Authorization': 'Bearer ' + token})
        with urllib.request.urlopen(req, timeout=30) as response: return json.load(response)
    attempt = ROOT / 'browser-attempts' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    attempt.mkdir(parents=True); downloads = attempt / 'downloads'; downloads.mkdir()
    state = {'status': 'RUNNING', 'started_at_utc': now(), 'account': 'pilot_viewer', 'cases': [], 'checks': [],
        'scope': 'Saved report parsing, persistence and literal display only; no new biological analysis or interpretation'}
    status_file = ROOT / 'verification-status.json'
    def check(case, name, passed, details):
        state['checks'].append({'case': case['key'], 'name': name, 'status': 'PASS' if passed else 'FAIL', 'details': details})
        write(status_file, state); print(case['key'] + ' / ' + name + ': ' + state['checks'][-1]['status'], flush=True)
    def without_nulls(value):
        if isinstance(value, dict): return {k: without_nulls(v) for k, v in value.items() if v is not None}
        if isinstance(value, list): return [without_nulls(v) for v in value]
        return value
    options = webdriver.ChromeOptions(); options.binary_location = '/snap/chromium/current/usr/lib/chromium-browser/chrome'
    options.add_argument('--headless=new'); options.add_argument('--window-size=1440,1100'); options.add_argument(f'--user-data-dir={attempt / "profile"}')
    options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
    browser = webdriver.Chrome(service=Service('/snap/bin/chromium.chromedriver', log_output=str(attempt / 'driver.log')), options=options)
    browser.execute_cdp_cmd('Browser.setDownloadBehavior', {'behavior': 'allow', 'downloadPath': str(downloads)})
    wait = WebDriverWait(browser, 30); base = 'http://127.0.0.1:18100'
    try:
        browser.get(base + '/login'); browser.find_element(By.ID, 'username').send_keys(account['username'])
        browser.find_element(By.ID, 'password').send_keys(account['password'], Keys.RETURN)
        wait.until(lambda d: '/groups' in d.current_url)
        for case in CASES:
            directory = ROOT / case['key']; imported = json.loads((directory / 'import-status.json').read_text())
            sid = imported['sample_id']; sample = get(sid); write(directory / 'sample-as-viewer.json', sample)
            rows = [r for field in ['typing_result', 'qc_result', 'element_type_result', 'species_prediction'] for r in sample.get(field, [])]
            by_type = {r['analysis_type']: r for r in rows}
            expected = json.loads((directory / 'expected-parser-output.json').read_text())['results']
            check(case, 'parser-to-stored-envelopes', set(by_type) == set(expected) and all(
                by_type[k]['status'] == v['status'] and without_nulls(by_type[k].get('result')) == without_nulls(v.get('value')) for k, v in expected.items()),
                {'envelopes_compared': len(expected), 'canonical_analyses': len({r['analysis_id'] for r in rows}),
                 'normalization': 'Optional null-valued mapping keys are omitted on both sides'})
            browser.get(base + '/groups'); field = wait.until(lambda d: d.find_element(By.ID, 'dt-search-0'))
            field.clear(); field.send_keys(case['external_id'])
            wait.until(lambda d: case['label'] in d.find_element(By.ID, 'sample-table').text)
            matching = browser.find_elements(By.CSS_SELECTOR, '#sample-table tbody tr[id]')
            check(case, 'overview-identity', len(matching) == 1 and case['label'] in matching[0].text, {'matching_rows': len(matching)})
            if case == CASES[0]:
                next(b for b in browser.find_elements(By.TAG_NAME, 'button') if b.text.strip() == 'CSV').click()
                wait.until(lambda _: bool(list(downloads.glob('*.csv'))))
                exported = next(downloads.glob('*.csv')); data = [r for r in csv.reader(exported.read_text(encoding='utf-8-sig').splitlines()) if r]
                check(case, 'filtered-csv-export', len(data) == 2 and case['label'] in data[1], {'rows_including_header': len(data)})
            browser.get(base + '/sample/' + sid); body = browser.find_element(By.TAG_NAME, 'body').text
            check(case, 'summary-opens', case['label'] in body and '500 Internal' not in browser.title, {'title': browser.title})
            browser.get(base + '/sample/' + sid + '?extended=true'); body = browser.find_element(By.TAG_NAME, 'body').text
            page_ok = case['label'] in body and '500 Internal' not in browser.title
            check(case, 'extended-summary-opens', page_ok, {'title': browser.title})
            if page_ok:
                scientific_name = by_type['species_prediction']['result']['scientific_name']
                check(case, 'stored-species-text-visible', scientific_name in body, {'literal_stored_label_visible': scientific_name in body})
                check(case, 'stored-k-o-labels-visible', all(str(by_type[k]['result'][f]) in body for k in ['k_type', 'o_type'] for f in ['locus', 'type']),
                    {'stored_label_fields_compared': 4})
                blank = []
                for selector, kind in [('#phenotype-heading .card', 'amr'), ('#virulence-heading .card', 'virulence')]:
                    if by_type[kind]['status'] != 'parsed': continue
                    cards = browser.find_elements(By.CSS_SELECTOR, selector)
                    if not cards or not any(c.find_element(By.CSS_SELECTOR, '.card-body').text.strip() for c in cards): blank.append(kind)
                check(case, 'populated-result-cards', not blank, {'parsed_result_types_without_readable_card': blank})
                check(case, 'score-object-not-empty-gene-list', 'No identified virulence factors.' not in ' '.join(body.split()),
                    {'stored_object_has_score': 'score' in by_type['virulence']['result'],
                     'unsupported_negative_wording_shown': 'No identified virulence factors.' in ' '.join(body.split())})
                qc = by_type['qc']['result']; displayed = {}
                for row in browser.find_elements(By.CSS_SELECTOR, '#qc-heading tbody tr'):
                    cells = row.find_elements(By.CSS_SELECTOR, 'th,td')
                    if len(cells) == 2: displayed[cells[0].text.lower()] = cells[1].text
                metrics = ['n_contigs', 'n50', 'largest_contig', 'total_length']
                check(case, 'qc-table-values', all(displayed.get(k.replace('_', ' ')) == format(qc[k], ',') for k in metrics), {'numeric_metrics_compared': len(metrics)})
                if case['companion_state'] == 'header-only':
                    check(case, 'absent-result-not-negative', by_type['amr']['status'] == 'absent' and 'No predicted resistance determinants.' not in body,
                        {'stored_status': by_type['amr']['status'], 'negative_wording_shown': 'No predicted resistance determinants.' in body})
                wait.until(lambda d: not d.find_element(By.CSS_SELECTOR, '#similar-samples-card spinner-element').is_displayed())
                browser.execute_script('window.scrollTo({top:0,behavior:"instant"})')
            browser.save_screenshot(str(attempt / (case['key'] + '-summary.png')))
            (attempt / (case['key'] + '-body.txt')).write_text(body)
            browser.get(base + '/sample/' + sid + '/metadata'); body = browser.find_element(By.TAG_NAME, 'body').text
            check(case, 'fixture-provenance-visible', 'One saved report/companion pair' in body and case['companion_state'] in body,
                {'fixture_origin_and_control_state_visible': 'One saved report/companion pair' in body and case['companion_state'] in body})
            state['cases'].append({**case, 'sample_id': sid, 'analysis_records': 1, 'view_descriptors': len(rows),
                'descriptor_statuses': {k: r['status'] for k, r in by_type.items()}})
        errors = [e for e in browser.get_log('browser') if e['level'] == 'SEVERE' and 'favicon' not in e['message']]
        failures = [c for c in state['checks'] if c['status'] == 'FAIL']
        state.update(status='COMPLETE_WITH_FINDINGS' if failures or errors else 'COMPLETE', finished_at_utc=now(),
            passed_checks=len(state['checks']) - len(failures), total_checks=len(state['checks']), console_errors=errors,
            screenshots=[{'path': str(p.relative_to(ROOT)), 'sha256': hashes(p)['sha256']} for p in sorted(attempt.glob('*.png'))])
        write(status_file, state); print(f'{state["passed_checks"]}/{state["total_checks"]} checks passed; {len(errors)} severe console entries')
    except Exception as error:
        browser.save_screenshot(str(attempt / 'failure.png'))
        state.update(status='FAILED', finished_at_utc=now(), error=str(error), attempt=str(attempt)); write(status_file, state)
        raise
    finally: browser.quit()


if __name__ == '__main__': main()
