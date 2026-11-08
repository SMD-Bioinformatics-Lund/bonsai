#!/usr/bin/env python3
"""Check saved-report bytes against stored values and an ordinary user's UI."""
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

from run_saved_report_case import CASE, DATA, EXTERNAL, FIXTURE_PIN, LABEL, PILOT, hashes, now, write


def main():
    imported = json.loads((CASE / 'import-status.json').read_text())
    assert imported['status'] == 'COMPLETE'
    credentials = json.loads((PILOT / 'bonsai/accounts.json').read_text())['pilot_viewer']
    body = urllib.parse.urlencode({'username': credentials['username'], 'password': credentials['password']}).encode()
    with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18101/token', data=body), timeout=30) as response:
        token = json.load(response)['access_token']
    request = urllib.request.Request('http://127.0.0.1:18101/samples/' + imported['sample_id'],
        headers={'Authorization': 'Bearer ' + token})
    with urllib.request.urlopen(request, timeout=30) as response:
        sample = json.load(response)
    write(CASE / 'sample-as-viewer.json', sample)
    attempt = CASE / 'browser-attempts' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    attempt.mkdir(parents=True)
    downloads = attempt / 'downloads'; downloads.mkdir()
    state = {'status': 'RUNNING', 'started_at_utc': now(), 'sample_id': sample['sample_id'],
        'account': 'pilot_viewer', 'checks': [], 'origin': 'Mixed saved SDK report fixtures',
        'scope': 'Literal report-to-store/display fidelity and ordinary UI; no biological interpretation'}
    status_file = CASE / 'verification-status.json'
    browser = None

    def check(name, passed, details):
        state['checks'].append({'name': name, 'status': 'PASS' if passed else 'FAIL', 'details': details})
        write(status_file, state)
        print(name + ': ' + state['checks'][-1]['status'], flush=True)

    try:
        raw = DATA / 'datasets/github/bonsai-sdk-saved-reports' / FIXTURE_PIN / 'raw/saureus'
        def first(filename):
            with (raw / filename).open() as handle:
                return next(csv.DictReader(handle, delimiter='\t'))
        spa = first('spatyper.tsv')
        typed = sample['typing_result'][0]['result']
        check('saved-to-stored-spatyper', typed == {'sequence_name': spa['Sequence name'],
            'repeats': spa['Repeats'], 'type': spa['Type']}, {'compared_fields': 3})
        quast = first('quast.tsv')
        mapping = {'total_length': 'Total length', 'reference_length': 'Reference length',
            'largest_contig': 'Largest contig', 'n_contigs': '# contigs', 'n50': 'N50', 'ng50': 'NG50',
            'assembly_gc': 'GC (%)', 'reference_gc': 'Reference GC (%)', 'duplication_ratio': 'Duplication ratio'}
        qc = {row['software']: row['result'] for row in sample['qc_result']}
        check('saved-to-stored-quast', all(float(qc['quast'][k]) == float(quast[v]) for k, v in mapping.items()),
            {'compared_fields': len(mapping)})
        with (raw / 'samtools_coverage.txt').open() as handle:
            coverage = list(csv.DictReader(handle, delimiter='\t'))
        mapping = {'start_pos': 'startpos', 'end_pos': 'endpos', 'n_reads': 'numreads', 'cov_bases': 'covbases',
            'coverage': 'coverage', 'mean_depth': 'meandepth', 'mean_base_quality': 'meanbaseq', 'mean_map_quality': 'meanmapq'}
        stored_coverage = qc['samtools']['contigs']
        check('saved-to-stored-coverage', len(stored_coverage) == len(coverage) and all(
            row['contig_name'] == source['#rname'] and all(float(row[k]) == float(source[v]) for k, v in mapping.items())
            for row, source in zip(stored_coverage, coverage)), {'contigs': len(coverage), 'compared_fields': 9 * len(coverage)})
        stats = {row.split('\t')[1].rstrip(':'): float(row.split('\t')[2])
            for row in (raw / 'samtools_stats.txt').read_text().splitlines() if row.startswith('SN\t')}
        expected_stats = {'n_reads': stats['raw total sequences'], 'n_read_pairs': stats['reads paired'] // 2,
            'n_mapped_reads': stats['reads mapped'], 'n_dup_reads': stats['reads duplicated'],
            'ins_size': stats['insert size average'], 'ins_size_dev': stats['insert size standard deviation']}
        check('saved-to-stored-read-statistics', all(qc['postalignqc'][k] == v for k, v in expected_stats.items()),
            {'compared_fields': len(expected_stats), 'read_pairs_derived_by': 'paired read count divided by two'})

        options = webdriver.ChromeOptions()
        options.binary_location = '/snap/chromium/current/usr/lib/chromium-browser/chrome'
        options.add_argument('--headless=new'); options.add_argument('--window-size=1440,1100')
        options.add_argument(f'--user-data-dir={attempt / "profile"}')
        options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
        browser = webdriver.Chrome(service=Service('/snap/bin/chromium.chromedriver', log_output=str(attempt / 'driver.log')), options=options)
        browser.execute_cdp_cmd('Browser.setDownloadBehavior', {'behavior': 'allow', 'downloadPath': str(downloads)})
        wait = WebDriverWait(browser, 30); base = 'http://127.0.0.1:18100'; sid = sample['sample_id']
        browser.get(base + '/login')
        browser.find_element(By.ID, 'username').send_keys(credentials['username'])
        browser.find_element(By.ID, 'password').send_keys(credentials['password'], Keys.RETURN)
        wait.until(lambda d: '/groups' in d.current_url)
        def filter_record():
            field = wait.until(lambda d: d.find_element(By.ID, 'dt-search-0'))
            field.clear(); field.send_keys(EXTERNAL)
            wait.until(lambda d: LABEL in d.find_element(By.ID, 'sample-table').text)
            return browser.find_elements(By.CSS_SELECTOR, '#sample-table tbody tr[id]')
        rows = filter_record()
        check('ordinary-filtered-overview', len(rows) == 1 and LABEL in rows[0].text,
            {'matching_rows': len(rows), 'expected_identity_present': LABEL in rows[0].text})
        browser.save_screenshot(str(attempt / 'overview.png'))
        next(link for link in rows[0].find_elements(By.TAG_NAME, 'a') if '/sample/' + sid in link.get_attribute('href')).click()
        wait.until(lambda d: '/sample/' + sid in d.current_url)
        body = browser.find_element(By.TAG_NAME, 'body').text
        check('ordinary-summary-identity', all(x in body for x in [LABEL, 'FIXTURE-SAUREUS-001', 'fixture-sdk-5789a9c'])
            and '500 Internal' not in browser.title, {'identity_and_fixture_version_preserved': True})
        browser.get(base + '/sample/' + sid + '?extended=true')
        headers = browser.find_elements(By.CSS_SELECTOR, '.card-header')
        def card(prefix):
            return next(x for x in headers if x.text.startswith(prefix)).find_element(By.XPATH, '..')
        body = browser.find_element(By.TAG_NAME, 'body').text
        (attempt / 'extended-body.txt').write_text(body)
        check('stored-to-displayed-spatype', typed['type'] in body and typed['repeats'] in body,
            {'type_and_repeat_text_preserved': typed['type'] in body and typed['repeats'] in body})
        check('omitted-analysis-not-presented-as-negative',
            not sample.get('element_type_result') and 'No predicted resistance determinants.' not in body,
            {'stored_element_result_count': len(sample.get('element_type_result', [])),
             'negative_wording_shown': 'No predicted resistance determinants.' in body})
        def metric_rows(element):
            return {cells[0].text.lower(): cells[1].text for row in element.find_elements(By.CSS_SELECTOR, 'tbody tr')
                if len(cells := row.find_elements(By.CSS_SELECTOR, 'th,td')) == 2}
        quast_rows = metric_rows(card('Quast'))
        check('stored-to-displayed-assembly-metrics', quast_rows['total length'] == format(qc['quast']['total_length'], ',')
            and quast_rows['n contigs'] == format(qc['quast']['n_contigs'], ','), {'compared_metrics': 2})
        paired = metric_rows(card('PostQc Alignment'))
        check('stored-to-displayed-read-pairs', paired['n read pairs'] == format(qc['postalignqc']['n_read_pairs'], ','),
            {'pairs': qc['postalignqc']['n_read_pairs'], 'display': paired['n read pairs']})
        rows = card('Samtools coverage').find_elements(By.CSS_SELECTOR, 'tbody tr')
        check('stored-to-displayed-contig-depths', len(rows) == len(stored_coverage) and all(
            float(row.find_elements(By.CSS_SELECTOR, 'th,td')[6].text.replace(',', '')) == round(source['mean_depth'], 2)
            for row, source in zip(rows, stored_coverage)), {'contigs_compared': len(stored_coverage), 'displayed_decimals': 2})
        wait.until(lambda d: not d.find_element(By.CSS_SELECTOR, '#similar-samples-card spinner-element').is_displayed())
        browser.execute_script('window.scrollTo({top:0,behavior:"instant"})')
        browser.save_screenshot(str(attempt / 'summary.png'))
        qc_element = browser.find_element(By.ID, 'qc-heading')
        browser.execute_script('window.scrollTo({top:arguments[0].getBoundingClientRect().top+window.scrollY-120,behavior:"instant"})', qc_element)
        clip = browser.execute_script('const r=arguments[0].getBoundingClientRect();return {x:r.x+window.scrollX,y:r.y+window.scrollY,width:r.width,height:r.height,scale:1}', qc_element)
        captured = browser.execute_cdp_cmd('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': True, 'clip': clip})
        (attempt / 'qc-values.png').write_bytes(base64.b64decode(captured['data']))
        browser.get(base + '/sample/' + sid + '/metadata')
        body = browser.find_element(By.TAG_NAME, 'body').text
        check('ordinary-fixture-provenance-metadata', 'Existing repository test reports' in body and 'Test scope' in body,
            {'fixture_origin_and_scope_visible': 'Existing repository test reports' in body and 'Test scope' in body})
        browser.save_screenshot(str(attempt / 'metadata.png'))
        browser.get(base + '/groups'); filter_record()
        next(x for x in browser.find_elements(By.TAG_NAME, 'button') if x.text.strip() == 'CSV').click()
        wait.until(lambda _: bool(list(downloads.glob('*.csv'))))
        exported = next(downloads.glob('*.csv'))
        data = [row for row in csv.reader(exported.read_text(encoding='utf-8-sig').splitlines()) if row]
        check('ordinary-filtered-csv-export', len(data) == 2 and LABEL in data[1],
            {'rows_including_header': len(data), 'fixture_identity_preserved': LABEL in data[1] if len(data) > 1 else False})
        errors = [x for x in browser.get_log('browser') if x['level'] == 'SEVERE' and 'favicon' not in x['message']]
        failures = [row['name'] for row in state['checks'] if row['status'] == 'FAIL']
        state.update(status='COMPLETE_WITH_FINDINGS' if failures else 'COMPLETE', finished_at_utc=now(), console_errors=errors,
            failed_checks=failures,
            findings=[
                {'id': 'MISSING-ANALYSIS-NEGATIVE-SUMMARY', 'priority': 'P1',
                 'title': 'An omitted analysis is presented as a negative summary',
                 'observed': 'No element-analysis report was uploaded, yet the summary says No predicted resistance determinants.',
                 'trigger_likelihood': 'Partial imports, interrupted uploads, or workflows that omit this analysis; frequency in routine complete uploads is unmeasured',
                 'fix_size': 'Small summary-template change to distinguish absent descriptors from a parsed empty result',
                 'production_code_changed': False},
                {'id': 'SA-TYPING-SURFACE-GAP', 'priority': 'P2',
                 'title': 'Stored SPA typing has no summary reading surface',
                 'observed': 'All three saved fields survive import, but the type and repeat text are absent from the extended summary.',
                 'trigger_likelihood': 'Every SPA result on the current summary; confirmed with this one saved fixture',
                 'fix_size': 'Small template/card addition; release-scope decision remains necessary',
                 'existing_report_issue': True, 'production_code_changed': False},
                {'id': 'NO-SIGNATURE-WIDGET-ERROR', 'priority': 'P2',
                 'title': 'Automatic similarity widget logs an error when no signature is present',
                 'observed': 'The unindexed saved-report case logs Similarity search failed and hides the card.',
                 'trigger_likelihood': 'Records without an index/signature; this case deliberately excludes them',
                 'fix_size': 'Small availability check and explicit unavailable state; no similarity computation was validated',
                 'production_code_changed': False}],
            screenshots=[{'path': str(p.relative_to(CASE)), 'sha256': hashes(p)['sha256']} for p in sorted(attempt.glob('*.png'))],
            limitations=['Saved mixed fixtures do not establish native producer compatibility or a coherent biological isolate',
                'No resistance/virulence, variant, reference-browser, signature or index coverage in this case'])
        checks_by_finding = {'MISSING-ANALYSIS-NEGATIVE-SUMMARY': 'omitted-analysis-not-presented-as-negative',
            'SA-TYPING-SURFACE-GAP': 'stored-to-displayed-spatype'}
        state['findings'] = [f for f in state['findings'] if
            checks_by_finding.get(f['id']) in failures or
            (f['id'] == 'NO-SIGNATURE-WIDGET-ERROR' and any('Similarity search failed' in e['message'] for e in errors))]
        write(status_file, state)
        print(f'{len(state["checks"])-len(failures)}/{len(state["checks"])} checks passed; {len(errors)} severe browser-console entries recorded', flush=True)
    except Exception as error:
        if browser:
            browser.save_screenshot(str(attempt / 'failure.png'))
            (attempt / 'failure-body.txt').write_text(browser.find_element(By.TAG_NAME, 'body').text)
        state.update(status='FAILED', finished_at_utc=now(), error=str(error), attempt=str(attempt))
        write(status_file, state)
        raise
    finally:
        if browser:
            browser.quit()


if __name__ == '__main__':
    main()
