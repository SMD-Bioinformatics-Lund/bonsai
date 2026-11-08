#!/usr/bin/env python3
"""Verify literal saved QC values and ordinary UI behavior for one TB profile."""
import base64
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

from tb_saved_qc_case import CASE, RAW, EXTERNAL, LABEL, LIMS, PILOT, hashes, now, write


def main():
    imported = json.loads((CASE / 'import-status.json').read_text())
    assert imported['status'] == 'COMPLETE'
    account = json.loads((PILOT / 'bonsai/accounts.json').read_text())['pilot_viewer']
    body = urllib.parse.urlencode({'username': account['username'], 'password': account['password']}).encode()
    with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18101/token', data=body), timeout=30) as response:
        token = json.load(response)['access_token']
    def get_sample():
        request = urllib.request.Request('http://127.0.0.1:18101/samples/' + imported['sample_id'],
            headers={'Authorization': 'Bearer ' + token})
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    sample = get_sample(); write(CASE / 'sample-as-viewer.json', sample)
    attempt = CASE / 'browser-attempts' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    attempt.mkdir(parents=True); downloads = attempt / 'downloads'; downloads.mkdir()
    status_file = CASE / 'verification-status.json'
    state = {'status': 'RUNNING', 'started_at_utc': now(), 'sample_id': sample['sample_id'],
        'account': 'pilot_viewer', 'checks': [], 'origin': 'Two saved repository QC fixtures',
        'scope': 'Numeric QC import and display, navigation, metadata and CSV export; no biological interpretation'}
    browser = None
    def check(name, passed, details):
        state['checks'].append({'name': name, 'status': 'PASS' if passed else 'FAIL', 'details': details})
        write(status_file, state); print(name + ': ' + state['checks'][-1]['status'], flush=True)
    try:
        check('viewer-identity-and-profile', sample['external_sample_id'] == EXTERNAL and sample['sample_name'] == LABEL
            and sample['lims_id'] == LIMS and sample['pipeline']['assay'] == 'mtuberculosis',
            {'fixture_identity_and_tb_profile_preserved': sample['pipeline']['assay'] == 'mtuberculosis'})
        check('qc-only-record-scope', len(sample['qc_result']) == 2 and
            len({r['analysis_id'] for r in sample['qc_result']}) == 2 and
            all(r['status'] == 'parsed' for r in sample['qc_result']) and
            not any(sample.get(k) for k in ['typing_result', 'element_type_result', 'species_prediction', 'genome_signature', 'ska_index', 'reference_genome_id']),
            {'qc_descriptors': len(sample['qc_result']), 'expected_canonical_analyses': 2})
        qc = {r['software']: r['result'] for r in sample['qc_result']}
        with (RAW / 'quast.tsv').open() as handle:
            quast = next(csv.DictReader(handle, delimiter='\t'))
        mapping = {'total_length': 'Total length', 'reference_length': 'Reference length',
            'largest_contig': 'Largest contig', 'n_contigs': '# contigs', 'n50': 'N50', 'ng50': 'NG50',
            'assembly_gc': 'GC (%)', 'reference_gc': 'Reference GC (%)', 'duplication_ratio': 'Duplication ratio'}
        check('saved-to-stored-quast', all(float(qc['quast'][k]) == float(quast[v]) for k, v in mapping.items()),
            {'compared_fields': len(mapping)})
        legacy = json.loads((RAW / 'bwa.qc').read_text())
        scalars = {k: float(v) for k, v in legacy.items() if k not in {'sample_id', 'pct_above_x'}}
        check('saved-to-stored-legacy-qc', all(float(qc['postalignqc'][k]) == v for k, v in scalars.items())
            and qc['postalignqc']['pct_above_x'] == legacy['pct_above_x'],
            {'scalar_metrics': len(scalars), 'coverage_bins': len(legacy['pct_above_x']),
             'limitation': 'Literal fixture preservation only; original metric semantics were not independently validated'})
        options = webdriver.ChromeOptions()
        options.binary_location = '/snap/chromium/current/usr/lib/chromium-browser/chrome'
        options.add_argument('--headless=new'); options.add_argument('--window-size=1440,1100')
        options.add_argument(f'--user-data-dir={attempt / "profile"}')
        options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
        browser = webdriver.Chrome(service=Service('/snap/bin/chromium.chromedriver', log_output=str(attempt / 'driver.log')), options=options)
        browser.execute_cdp_cmd('Browser.setDownloadBehavior', {'behavior': 'allow', 'downloadPath': str(downloads)})
        wait = WebDriverWait(browser, 30); base = 'http://127.0.0.1:18100'; sid = sample['sample_id']
        browser.get(base + '/login')
        browser.find_element(By.ID, 'username').send_keys(account['username'])
        browser.find_element(By.ID, 'password').send_keys(account['password'], Keys.RETURN)
        wait.until(lambda d: '/groups' in d.current_url)
        def filter_record():
            field = wait.until(lambda d: d.find_element(By.ID, 'dt-search-0'))
            field.clear(); field.send_keys(EXTERNAL)
            wait.until(lambda d: LABEL in d.find_element(By.ID, 'sample-table').text)
            return browser.find_elements(By.CSS_SELECTOR, '#sample-table tbody tr[id]')
        rows = filter_record()
        check('ordinary-filtered-overview', len(rows) == 1 and LABEL in rows[0].text, {'matching_rows': len(rows)})
        browser.save_screenshot(str(attempt / 'overview.png'))
        next(a for a in rows[0].find_elements(By.TAG_NAME, 'a') if '/sample/' + sid in a.get_attribute('href')).click()
        wait.until(lambda d: '/sample/' + sid in d.current_url)
        body = browser.find_element(By.TAG_NAME, 'body').text
        check('ordinary-summary-identity', all(s in body for s in [LABEL, LIMS, 'fixture-sdk-5789a9c'])
            and '500 Internal' not in browser.title, {'identity_and_fixture_version_visible': all(s in body for s in [LABEL, LIMS, 'fixture-sdk-5789a9c'])})
        browser.get(base + '/sample/' + sid + '?extended=true')
        body = browser.find_element(By.TAG_NAME, 'body').text
        check('extended-summary-opens', LABEL in body and 'Quast' in body and 'PostQc Alignment' in body
            and '500 Internal' not in browser.title, {'quality_report_cards_visible': 'Quast' in body and 'PostQc Alignment' in body})
        check('omitted-analysis-not-presented-as-negative', 'No predicted resistance determinants.' not in body,
            {'stored_element_result_count': len(sample.get('element_type_result', [])),
             'negative_wording_shown': 'No predicted resistance determinants.' in body})
        def card(prefix):
            return next(h for h in browser.find_elements(By.CSS_SELECTOR, '.card-header') if h.text.startswith(prefix)).find_element(By.XPATH, '..')
        def metric_rows(element):
            return {cells[0].text.lower(): cells[1].text for row in element.find_elements(By.CSS_SELECTOR, 'tbody tr')
                if len(cells := row.find_elements(By.CSS_SELECTOR, 'th,td')) == 2}
        def display_matches(values, displayed):
            return all(float(displayed[k.replace('_', ' ')].replace(',', '')) == round(float(v), 2) for k, v in values.items())
        quast_display = metric_rows(card('Quast'))
        check('stored-to-displayed-assembly-metrics', display_matches(qc['quast'], quast_display),
            {'compared_metrics': len(qc['quast']), 'displayed_decimals_at_most': 2})
        post_display = metric_rows(card('PostQc Alignment'))
        check('stored-to-displayed-legacy-qc', display_matches(scalars, post_display),
            {'compared_metrics': len(scalars), 'producer_version': 'Explicit synthetic placeholder: 0.0.0+fixture.unknown'})
        plot = wait.until(lambda d: d.execute_script('return document.querySelector("#qcPlot")?.data?.[0] || null'))
        check('stored-to-displayed-coverage-plot', list(plot['y']) == list(legacy['pct_above_x'].values())
            and list(plot['x']) == [k + 'X' for k in legacy['pct_above_x']], {'bins_compared': len(legacy['pct_above_x'])})
        wait.until(lambda d: not d.find_element(By.CSS_SELECTOR, '#similar-samples-card spinner-element').is_displayed())
        browser.execute_script('window.scrollTo({top:0,behavior:"instant"})'); browser.save_screenshot(str(attempt / 'summary.png'))
        element = browser.find_element(By.ID, 'qc-heading')
        browser.execute_script('window.scrollTo({top:arguments[0].getBoundingClientRect().top+window.scrollY-120,behavior:"instant"})', element)
        clip = browser.execute_script('const r=arguments[0].getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height,scale:1}', element)
        capture = browser.execute_cdp_cmd('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': True, 'clip': clip})
        (attempt / 'qc-values.png').write_bytes(base64.b64decode(capture['data']))
        browser.get(base + '/sample/' + sid + '/metadata'); body = browser.find_element(By.TAG_NAME, 'body').text
        check('ordinary-fixture-provenance-metadata', 'Existing repository QC reports' in body and 'Test scope' in body,
            {'fixture_origin_and_scope_visible': 'Existing repository QC reports' in body and 'Test scope' in body})
        browser.save_screenshot(str(attempt / 'metadata.png'))
        browser.get(base + '/sample/' + sid + '/resistance/variants'); body = browser.find_element(By.TAG_NAME, 'body').text
        check('omitted-detail-availability-message', 'No stored TBProfiler variant result' in body and '500 Internal' not in browser.title
            and 'No predicted resistance determinants.' not in body, {'unavailability_message_visible': 'No stored TBProfiler variant result' in body})
        browser.save_screenshot(str(attempt / 'unavailable-detail.png'))
        browser.get(base + '/groups'); filter_record()
        next(b for b in browser.find_elements(By.TAG_NAME, 'button') if b.text.strip() == 'CSV').click()
        wait.until(lambda _: bool(list(downloads.glob('*.csv'))))
        exported = next(downloads.glob('*.csv'))
        data = [r for r in csv.reader(exported.read_text(encoding='utf-8-sig').splitlines()) if r]
        check('ordinary-filtered-csv-export', len(data) == 2 and LABEL in data[1], {'rows_including_header': len(data)})
        refreshed = get_sample()
        check('read-only-session-preserves-qc', refreshed['qc_result'] == sample['qc_result'], {'qc_descriptor_count_after_session': len(refreshed['qc_result'])})
        errors = [e for e in browser.get_log('browser') if e['level'] == 'SEVERE' and 'favicon' not in e['message']]
        failures = [c['name'] for c in state['checks'] if c['status'] == 'FAIL']; findings = []
        if 'omitted-analysis-not-presented-as-negative' in failures:
            findings.append({'id': 'MISSING-ANALYSIS-NEGATIVE-SUMMARY', 'priority': 'P1',
                'title': 'An omitted analysis is presented as a negative summary',
                'observed': 'The TB-profile QC-only case has no element-analysis reports, yet the extended summary presents negative-result wording.',
                'trigger_likelihood': 'Partial or QC-only imports; routine full-workflow frequency is unmeasured',
                'fix_size': 'Small summary-template change distinguishing absent descriptors from a parsed empty result',
                'production_code_changed': False, 'reproduces_saureus_finding': True})
        if any('Similarity search failed' in e['message'] for e in errors):
            findings.append({'id': 'NO-SIGNATURE-WIDGET-ERROR', 'priority': 'P2',
                'title': 'Automatic similarity widget logs an error when no signature is present',
                'observed': 'The automatic widget logs an error and disappears for this deliberately unindexed QC-only case.',
                'trigger_likelihood': 'Records without an index/signature',
                'fix_size': 'Small availability check and explicit unavailable state; similarity computation remains untested',
                'production_code_changed': False, 'reproduces_saureus_finding': True})
        state.update(status='COMPLETE_WITH_FINDINGS' if failures or errors else 'COMPLETE', finished_at_utc=now(),
            failed_checks=failures, findings=findings, console_errors=errors,
            screenshots=[{'path': str(p.relative_to(CASE)), 'sha256': hashes(p)['sha256']} for p in sorted(attempt.glob('*.png'))],
            limitations=['Saved QC reports only; no native producer, biological typing or resistance/virulence/lineage output was tested',
                'Fixture provenance and numeric preservation do not establish biological accuracy or sample coherence',
                'Legacy producer version is unknown; 0.0.0+fixture.unknown is a synthetic version placeholder'])
        write(status_file, state)
        print(f'{len(state["checks"])-len(failures)}/{len(state["checks"])} checks passed; {len(errors)} severe browser-console entries', flush=True)
    except Exception as error:
        if browser:
            browser.save_screenshot(str(attempt / 'failure.png'))
            (attempt / 'failure-body.txt').write_text(browser.find_element(By.TAG_NAME, 'body').text)
        state.update(status='FAILED', finished_at_utc=now(), error=str(error), attempt=str(attempt)); write(status_file, state)
        raise
    finally:
        if browser:
            browser.quit()


if __name__ == '__main__':
    main()
