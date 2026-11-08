#!/usr/bin/env python3
"""Check the generated local review's links, mobile layout and key content."""
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait

from verify_minimal_prs import ROOT, DATA

SITE=DATA/'docs/development-findings'
OUTPUT=SITE/'development'


class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.ids=set()
    def handle_starttag(self,tag,attributes):
        a=dict(attributes)
        if 'id' in a:self.ids.add(a['id'])
        if tag=='a' and 'href' in a:self.links.append(a['href'])
        if tag in {'img','script'} and 'src' in a:self.links.append(a['src'])
        if tag=='source' and 'srcset' in a:self.links.append(a['srcset'].split()[0])


def run():
    directory=ROOT/'report-qa';directory.mkdir(exist_ok=True)
    documents={path:Links() for path in SITE.rglob('*.html')}
    for path,parser in documents.items():parser.feed(path.read_text())
    checked=0;errors=[]
    for path,parser in documents.items():
        if not path.is_relative_to(OUTPUT):continue
        for href in parser.links:
            url=urlparse(href)
            if url.scheme or url.netloc:continue
            target=(path.parent/unquote(url.path)).resolve() if url.path else path.resolve()
            if target.is_dir():target=target/'index.html'
            checked+=1
            if not target.exists():errors.append({'page':str(path),'link':href,'error':'missing target'})
            elif url.fragment and target.suffix=='.html':
                # Compare resolved paths to preserve the data-drive compatibility link.
                found=next((p for p in documents if p.resolve()==target),None)
                if found is None or unquote(url.fragment) not in documents[found].ids:errors.append({'page':str(path),'link':href,'error':'missing anchor'})
    assert not errors,errors
    options=webdriver.ChromeOptions();options.binary_location='/snap/chromium/current/usr/lib/chromium-browser/chrome'
    options.add_argument('--headless=new');options.add_argument(f'--user-data-dir={directory/"browser-profile"}');options.add_argument('--window-size=1440,1100')
    options.set_capability('goog:loggingPrefs',{'browser':'ALL'})
    browser=webdriver.Chrome(service=Service('/snap/bin/chromium.chromedriver',log_output=str(directory/'browser-driver.log')),options=options)
    states=[]
    try:
        for width in [320,390,1440]:
            browser.set_window_size(width,1100)
            for page in ['index.html#fixes','index.html#PRIVATE-RECORD-SCOPE','index.html#screenshots','prs/index.html','prs/recovery-comment-retry.html']:
                browser.get('http://127.0.0.1:8001/development/'+page)
                WebDriverWait(browser,10).until(lambda d:d.execute_script('return document.readyState')=='complete')
                if page.endswith('#screenshots'):
                    for element in browser.find_elements('css selector','#screenshots img'):
                        browser.execute_script('arguments[0].scrollIntoView();',element)
                        WebDriverWait(browser,10).until(lambda _:element.get_property('complete') and element.get_property('naturalWidth')>0)
                    browser.execute_script('document.getElementById("screenshots").scrollIntoView();')
                result=browser.execute_script('''return {width:innerWidth,scroll_width:document.documentElement.scrollWidth,title:document.title,
                    broken_images:[...document.images].filter(x=>(x.loading!=="lazy"&&!x.complete)||(x.complete&&!x.naturalWidth)).map(x=>x.src),
                    text:document.body.innerText,console_placeholder:null};''')
                assert result['scroll_width']<=result['width']+1,{k:v for k,v in result.items() if k!='text'}
                assert not result['broken_images'],result['broken_images']
                assert 'Traceback' not in result['text'] and '404 Not Found' not in result['title'],result
                if page=='index.html#fixes':assert '39 local branches for 38 findings' in result['text'] and '91 focused checks' in result['text']
                if page.endswith('recovery-comment-retry.html'):assert 'pr/recovery-comment-identities' in result['text'] and '48/-14' in result['text']
                result.pop('text');result['page']=page;result['requested_width']=width
                filename=f'{width}-'+page.replace('.html','').replace('/','-').replace('#','-')+'.png'
                browser.save_screenshot(str(directory/filename));result['screenshot']=filename
                states.append(result)
        console=browser.get_log('browser')
        serious=[x for x in console if x['level']=='SEVERE' and 'favicon' not in x['message']]
        assert not serious,serious
    finally:browser.quit()
    record={'created_at':datetime.now(timezone.utc).isoformat(),'checked_links':checked,'link_errors':errors,'browser_states':states}
    (directory/'html-qa.json').write_text(json.dumps(record,indent=2)+'\n')
    print(f'{checked} local links/anchors; {len(states)} browser layouts; no horizontal overflow or broken images')


if __name__=='__main__':run()
