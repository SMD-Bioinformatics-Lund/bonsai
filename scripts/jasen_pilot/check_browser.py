#!/usr/bin/env python3
"""Check the real imported reference record as an ordinary interactive user."""
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from common import RUN, hashes, now, write


def main():
    imported=json.loads((RUN/'bonsai/import-status.json').read_text());assert imported['status']=='COMPLETE'
    credentials=json.loads((RUN/'bonsai/accounts.json').read_text())['pilot_viewer']
    attempt=RUN/'bonsai/browser-attempts'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S');attempt.mkdir(parents=True)
    downloads=attempt/'downloads';downloads.mkdir()
    options=webdriver.ChromeOptions();options.binary_location='/snap/chromium/current/usr/lib/chromium-browser/chrome'
    options.add_argument('--headless=new');options.add_argument('--window-size=1440,1100');options.add_argument(f'--user-data-dir={attempt/"profile"}')
    options.set_capability('goog:loggingPrefs',{'browser':'ALL'})
    options.add_experimental_option('prefs',{'download.default_directory':str(downloads),'download.prompt_for_download':False})
    browser=webdriver.Chrome(service=Service('/snap/bin/chromium.chromedriver',log_output=str(attempt/'driver.log')),options=options)
    browser.execute_cdp_cmd('Browser.setDownloadBehavior',{'behavior':'allow','downloadPath':str(downloads)})
    wait=WebDriverWait(browser,30);checks=[]
    def check(name,condition,observed):
        image=attempt/(name+'.png');browser.save_screenshot(str(image))
        row={'name':name,'status':'PASS' if condition else 'FAIL','observed':observed,'screenshot':str(image.relative_to(RUN)),'screenshot_sha256':hashes(image)['sha256']}
        checks.append(row);print(name+': '+row['status'],flush=True)
        write(RUN/'bonsai/browser-status.json',{'status':'RUNNING','checks':checks,'sample_id':imported['sample_id']})
        assert condition,row
    base='http://127.0.0.1:18100';sid=imported['sample_id'];label='Public reference MG1655 (ERR022075)'
    try:
        browser.get(base+'/login')
        browser.find_element(By.ID,'username').send_keys(credentials['username'])
        browser.find_element(By.ID,'password').send_keys(credentials['password'],Keys.RETURN)
        wait.until(lambda d:'/groups' in d.current_url)
        field=wait.until(lambda d:d.find_element(By.ID,'dt-search-0'));field.send_keys('pilot_k12_err022075')
        wait.until(lambda d:label in d.find_element(By.ID,'sample-table').text)
        rows=browser.find_elements(By.CSS_SELECTOR,'#sample-table tbody tr[id]')
        check('ordinary-overview',len(rows)==1 and label in rows[0].text,{'matching_rows':len(rows),'identity_present':label in browser.find_element(By.ID,'sample-table').text})
        link=next(x for x in rows[0].find_elements(By.TAG_NAME,'a') if '/sample/'+sid in x.get_attribute('href'))
        link.click();wait.until(lambda d:'/sample/'+sid in d.current_url)
        body=browser.find_element(By.TAG_NAME,'body').text
        check('ordinary-summary',all(x in body for x in [label,'K12-PILOT-001','1.4.1']) and '500 Internal Server Error' not in browser.title,
            {'name_present':label in body,'lims_present':'K12-PILOT-001' in body,'pipeline_version_present':'1.4.1' in body})
        for name,path,expected in [('extended-summary','/sample/'+sid+'?extended=true',label),('metadata','/sample/'+sid+'/metadata','Metadata'),
            ('supported-detail-scope','/sample/'+sid+'/resistance/variants','Other stored result types are not displayed')]:
            browser.get(base+path);body=browser.find_element(By.TAG_NAME,'body').text
            check(name,expected in body and not any(x in browser.title for x in ['500 Internal','404 Not Found']),{'expected_label_present':expected in body,'title':browser.title})
        browser.get(base+'/groups');wait.until(lambda d:d.find_elements(By.ID,'dt-search-0'))
        browser.find_element(By.ID,'dt-search-0').send_keys('pilot_k12_err022075')
        wait.until(lambda d:label in d.find_element(By.ID,'sample-table').text)
        next(x for x in browser.find_elements(By.TAG_NAME,'button') if x.text.strip()=='CSV').click()
        wait.until(lambda _:bool(list(downloads.glob('*.csv'))))
        exported=next(downloads.glob('*.csv'));data=[row for row in csv.reader(exported.read_text(encoding='utf-8-sig').splitlines()) if row]
        check('ordinary-csv-export',len(data)==2 and label in data[1],{'rows_including_header':len(data),'identity_present':label in data[1] if len(data)>1 else False,'file':str(exported.relative_to(RUN))})
        errors=[x for x in browser.get_log('browser') if x['level']=='SEVERE' and 'favicon' not in x['message']]
        write(attempt/'console-errors.json',errors)
        # Record unrelated automatic-widget failures separately from the checks.
        write(RUN/'bonsai/browser-status.json',{'status':'COMPLETE','finished_at_utc':now(),'sample_id':sid,'account':'pilot_viewer','checks':checks,'console_errors':errors,
            'scope':'Ordinary-user navigation, literal identity/version, supported-view scope and CSV export; no decision submitted'})
    except Exception as error:
        browser.save_screenshot(str(attempt/'failure.png'))
        write(RUN/'bonsai/browser-status.json',{'status':'FAILED','finished_at_utc':now(),'sample_id':sid,
            'checks':checks,'error':str(error),'failure_screenshot':str((attempt/'failure.png').relative_to(RUN))})
        raise
    finally:browser.quit()


if __name__=='__main__':main()
