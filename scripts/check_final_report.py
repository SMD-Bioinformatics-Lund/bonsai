#!/usr/bin/env python3
"""Delivery QA for the requested final report: links, PDF text, refs and mobile UI."""
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlparse
from urllib.request import urlopen


SITE = Path('/home/jakob/data/codex/bonsai/docs/development-findings')
ROOT = SITE / 'final'
QA = Path('/home/jakob/data/codex/bonsai/runs/2026-11-08-final-report/qa')
RELEASE_PYTHON = Path('/home/jakob/data/codex/bonsai/environments/release-test/bin/python')


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids = [], set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a:
            self.ids.add(a['id'])
        if tag == 'a' and a.get('href'):
            self.links.append(a['href'])
        if tag == 'img' and a.get('src'):
            self.links.append(a['src'])
        if tag == 'source' and a.get('srcset'):
            self.links.append(a['srcset'].split()[0])


def load(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def browser_check():
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.support.ui import WebDriverWait
    options = webdriver.ChromeOptions()
    options.binary_location = '/snap/chromium/current/usr/lib/chromium-browser/chrome'
    for argument in ['--headless=new', '--disable-dev-shm-usage', '--no-first-run',
                     '--user-data-dir=' + str(QA / 'browser-profile')]:
        options.add_argument(argument)
    options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
    browser = webdriver.Chrome(service=Service('/snap/bin/chromium.chromedriver',
        log_output=str(QA / 'browser-driver.log')), options=options)
    states = []
    try:
        for width in [320, 390, 1440]:
            browser.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {
                'width': width, 'height': 1000, 'deviceScaleFactor': 1, 'mobile': width < 600})
            for page in ['index.html', 'index.html#coverage', 'index.html#KLEBORATE-SUMMARY-DISPATCH',
                         'index.html#branches', 'index.html#screenshots', 'technical.html']:
                browser.get('http://127.0.0.1:8001/final/' + page)
                WebDriverWait(browser, 15).until(lambda d: d.execute_script('return document.readyState') == 'complete')
                if '#screenshots' in page:
                    for element in browser.find_elements('css selector', '#screenshots img'):
                        browser.execute_script('arguments[0].scrollIntoView();', element)
                        WebDriverWait(browser, 15).until(lambda _: element.get_property('complete') and element.get_property('naturalWidth') > 0)
                    browser.execute_script('document.getElementById("screenshots").scrollIntoView();')
                result = browser.execute_script('''return {
                    width:innerWidth, scroll_width:document.documentElement.scrollWidth,
                    title:document.title, text:document.body.innerText,
                    broken_images:[...document.images].filter(x=>(x.loading!=="lazy"&&!x.complete)||(x.complete&&!x.naturalWidth)).map(x=>x.src)
                };''')
                assert result['width'] == width, result
                assert result['scroll_width'] <= width + 1, {k:v for k,v in result.items() if k != 'text'}
                assert not result['broken_images'], result['broken_images']
                assert '404 Not Found' not in result['title'] and 'Traceback' not in result['text']
                if page.startswith('index'):
                    assert '44 verified local branches cover 43 findings' in result['text']
                    assert 'MISSING-ANALYSIS-NEGATIVE-SUMMARY' in result['text']
                    assert 'pr/kleborate-kaptive-nesting' in result['text']
                    assert 'None prepared' in result['text']
                    assert len(browser.find_elements('css selector', '.issue')) == 64
                result.pop('text')
                name = f'{width}-' + page.replace('.html', '').replace('#', '-') + '.png'
                browser.save_screenshot(str(QA / name))
                result.update({'page': page, 'screenshot': name})
                states.append(result)
        console = browser.get_log('browser')
        serious = [x for x in console if x['level'] == 'SEVERE' and 'favicon' not in x['message']]
        assert not serious, serious
    finally:
        browser.quit()
    write(QA / 'browser.json', {'states': states, 'serious_console_errors': serious})
    print(f'{len(states)} browser states passed at 320, 390 and 1440 CSS pixels')


def main():
    QA.mkdir(parents=True, exist_ok=True)
    if '--browser' in sys.argv:
        browser_check()
        return
    from pypdf import PdfReader
    parsers = {}
    def parse(path):
        path = path.resolve()
        if path not in parsers:
            parser = Links()
            parser.feed(path.read_text())
            parsers[path] = parser
        return parsers[path]
    links = 0
    for page in ROOT.glob('*.html'):
        for href in parse(page).links:
            url = urlparse(href)
            if url.scheme or url.netloc:
                continue
            target = (page.parent / unquote(url.path)).resolve() if url.path else page.resolve()
            if target.is_dir():
                target = target / 'index.html'
            assert target.exists(), (page, href)
            if url.fragment and target.suffix == '.html':
                assert unquote(url.fragment) in parse(target).ids, (page, href, 'anchor')
            links += 1
    ledger, branches = load(ROOT / 'data/issues.json'), load(ROOT / 'data/branches.json')
    pdf = ROOT / 'output/pdf/bonsai-final-test-report.pdf'
    reader = PdfReader(pdf)
    text = '\n'.join(p.extract_text() or '' for p in reader.pages)
    compact = ''.join(text.split())
    assert len(reader.pages) >= 10
    assert all(x['id'] in text for x in ledger['findings'])
    assert all(''.join(x['branch'].split()) in compact for x in branches['branches'])
    assert not any(x in text for x in ['\ufffd', '\u25a0', ':codex-file-citation'])
    assert all(len(p.extract_text() or '') > 100 for p in reader.pages)
    assert len(ledger['findings']) == 64 and len(branches['branches']) == 44
    assert len([x for x in ledger['findings'] if not x['candidates']]) == 21
    assert sum(x['priority'] in {'P0', 'P1'} and not x['candidates'] for x in ledger['findings']) == 2
    preservation = load(ROOT / 'data/preservation.json')
    for name, expected in preservation['files'].items():
        assert sha256(Path(name).read_bytes()).hexdigest() == expected, name
    responses = []
    for base in ['http://127.0.0.1:8001/final/', 'http://100.90.51.21:8001/final/']:
        for relative in ['', 'output/pdf/bonsai-final-test-report.pdf', 'data/issues.csv']:
            with urlopen(base + relative, timeout=15) as response:
                payload = response.read()
                assert response.status == 200
                if relative.endswith('.pdf'):
                    assert payload == pdf.read_bytes()
                    assert response.headers.get_content_type() == 'application/pdf'
                responses.append({'url': base + relative, 'status': response.status, 'bytes': len(payload)})
    public_files = [p for p in ROOT.rglob('*') if p.is_file() and p.suffix in {'.html', '.json', '.csv', '.svg'}]
    token = re.compile(rb'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.')
    assert not any(token.search(p.read_bytes()) for p in public_files)
    subprocess.run([str(RELEASE_PYTHON), str(Path(__file__)), '--browser'], check=True)
    record = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'status': 'PASS',
        'local_links_and_anchors': links, 'pdf_pages': len(reader.pages),
        'pdf_sha256': sha256(pdf.read_bytes()).hexdigest(), 'all_64_issue_ids_in_pdf': True,
        'all_44_branch_names_in_pdf': True, 'earlier_files_unchanged': len(preservation['files']),
        'http_checks': responses, 'browser': load(QA / 'browser.json'),
        'visual_review': 'Pending rendered-page inspection'}
    write(ROOT / 'data/report-qa.json', record)
    print(json.dumps({k:v for k,v in record.items() if k not in {'http_checks', 'browser'}}))


if __name__ == '__main__':
    main()
