#!/usr/bin/env python3
"""Compare literal control values across producer files, stored records and UI."""
import csv
import base64
from datetime import datetime, timezone
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from common import RUN, hashes, now, write


def main():
    attempt=RUN/'bonsai/fidelity-attempts'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    attempt.mkdir(parents=True);checks=[];browser=None
    state={'status':'RUNNING','started_at_utc':now(),'checks':checks,
        'scope':'Literal data and display fidelity for one public control; no biological interpretation'}
    file=RUN/'bonsai/fidelity-status.json'
    def check(name,passed,details):
        checks.append({'name':name,'status':'PASS' if passed else 'FAIL','details':details});write(file,state)
        assert passed,name
    try:
        sample=json.loads((RUN/'bonsai/sample-after-pair-count.json').read_text())
        output=RUN/'output/ecoli';sid=sample['sample_id'];state['sample_id']=sid
        mlst=json.loads((output/'mlst/pilot_k12_err022075_mlst.json').read_text())[0]
        typed=next(x['result'] for x in sample['typing_result'] if x['analysis_type']=='mlst')
        check('producer-to-stored-mlst',typed=={'scheme':mlst['scheme'],'sequence_type':int(mlst['sequence_type']),
            'alleles':{k:int(v) for k,v in mlst['alleles'].items()}},{'compared_fields':9})
        with (output/'quast/pilot_k12_err022075_quast.tsv').open() as handle:quast=next(csv.DictReader(handle,delimiter='\t'))
        mapping={'total_length':'Total length','reference_length':'Reference length','largest_contig':'Largest contig',
            'n_contigs':'# contigs','n50':'N50','ng50':'NG50','assembly_gc':'GC (%)',
            'reference_gc':'Reference GC (%)','duplication_ratio':'Duplication ratio'}
        stored=next(x['result'] for x in sample['qc_result'] if x['software']=='quast')
        check('producer-to-stored-quast',all(float(stored[k])==float(quast[v]) for k,v in mapping.items()),{'compared_fields':len(mapping)})
        with (output/'coverage/pilot_k12_err022075_bwa_mapcoverage.txt').open() as handle:coverage=next(csv.DictReader(handle,delimiter='\t'))
        mapping={'start_pos':'startpos','end_pos':'endpos','n_reads':'numreads','cov_bases':'covbases',
            'coverage':'coverage','mean_depth':'meandepth','mean_base_quality':'meanbaseq','mean_map_quality':'meanmapq'}
        stored_coverage=next(x['result']['contigs'][0] for x in sample['qc_result'] if x['software']=='samtools')
        check('producer-to-stored-coverage',stored_coverage['contig_name']==coverage['#rname'] and
            all(float(stored_coverage[k])==float(coverage[v]) for k,v in mapping.items()),{'compared_fields':len(mapping)+1})
        credentials=json.loads((RUN/'bonsai/accounts.json').read_text())['pilot_viewer']
        options=webdriver.ChromeOptions();options.binary_location='/snap/chromium/current/usr/lib/chromium-browser/chrome'
        options.add_argument('--headless=new');options.add_argument('--window-size=1440,1100')
        options.add_argument(f'--user-data-dir={attempt/"profile"}');options.set_capability('goog:loggingPrefs',{'browser':'ALL'})
        browser=webdriver.Chrome(service=Service('/snap/bin/chromium.chromedriver',log_output=str(attempt/'driver.log')),options=options)
        wait=WebDriverWait(browser,30);base='http://127.0.0.1:18100'
        browser.get(base+'/login');browser.find_element(By.ID,'username').send_keys(credentials['username'])
        browser.find_element(By.ID,'password').send_keys(credentials['password'],Keys.RETURN)
        wait.until(lambda d:'/groups' in d.current_url);browser.get(base+'/sample/'+sid+'?extended=true')
        wait.until(lambda d:not d.find_element(By.CSS_SELECTOR,'#similar-samples-card spinner-element').is_displayed())
        check('background-widget-settles',True,{'similarity_card_visible':browser.find_element(By.ID,'similar-samples-card').is_displayed(),
            'inventory_size':1,'scope':'Automatic single-control widget; no multi-sample comparison available'})
        headers=browser.find_elements(By.CSS_SELECTOR,'.card-header')
        def card(prefix):return next(x for x in headers if x.text.startswith(prefix)).find_element(By.XPATH,'..')
        mlst_card=card('MLST');rows=mlst_card.find_elements(By.CSS_SELECTOR,'table tr')
        genes=[x.text for x in rows[0].find_elements(By.CSS_SELECTOR,'th,td')[1:]]
        numbers=[int(x.text) for x in rows[1].find_elements(By.CSS_SELECTOR,'th,td')[1:]]
        check('stored-to-displayed-mlst',dict(zip(genes,numbers))==typed['alleles'] and typed['scheme'] in mlst_card.text
            and 'ST '+str(typed['sequence_type']) in mlst_card.text,{'ordered_locus_values_compared':len(genes)})
        def metric_rows(element):
            return {cells[0].text.lower():cells[1].text for row in element.find_elements(By.CSS_SELECTOR,'tbody tr')
                if len(cells:=row.find_elements(By.CSS_SELECTOR,'th,td'))==2}
        quast_rows=metric_rows(card('Quast'))
        check('stored-to-displayed-total-length',quast_rows['total length']==format(int(quast['Total length']),','),{'metric':'total_length'})
        paired=metric_rows(card('PostQc Alignment'))
        expected=json.loads((RUN/'bonsai/pair-count-correction-status.json').read_text())['validated_input_pairs']
        check('input-to-displayed-read-pairs',paired['n read pairs']==format(expected,','),{'input_pairs':expected,'display':paired['n read pairs']})
        body=card('Samtools coverage');cells=body.find_elements(By.CSS_SELECTOR,'tbody tr')[0].find_elements(By.CSS_SELECTOR,'th,td')
        check('stored-to-displayed-mean-depth',float(cells[6].text.replace(',',''))==round(float(coverage['meandepth']),2),{'displayed_decimals':2})
        browser.execute_script('window.scrollTo(0,0)');browser.save_screenshot(str(attempt/'summary-settled.png'))
        qc=browser.find_element(By.ID,'qc-heading')
        browser.execute_script('window.scrollTo({top:arguments[0].getBoundingClientRect().top+window.scrollY-120,behavior:"instant"})',qc)
        clip=browser.execute_script('const r=arguments[0].getBoundingClientRect();return {x:r.x+window.scrollX,y:r.y+window.scrollY,width:r.width,height:r.height,scale:1}',qc)
        captured=browser.execute_cdp_cmd('Page.captureScreenshot',{'format':'png','captureBeyondViewport':True,'clip':clip})
        (attempt/'qc-values.png').write_bytes(base64.b64decode(captured['data']))
        errors=[x for x in browser.get_log('browser') if x['level']=='SEVERE' and 'favicon' not in x['message']]
        assert not [x for x in errors if 'Similarity search failed' not in x['message']],errors
        state.update(status='COMPLETE',finished_at_utc=now(),console_errors=errors,
            observations=[{'id':'SINGLE-CONTROL-SIMILARITY','apparent_priority':'P2',
                'observed':'Automatic similarity widget logs an error for a one-record inventory and hides the card',
                'scope':'Single-control empty-neighbour handling only; multi-sample behavior untested'}]
                if any('Similarity search failed' in x['message'] for x in errors) else [],
            screenshots=[{'path':str(p.relative_to(RUN)),'sha256':hashes(p)['sha256']} for p in sorted(attempt.glob('*.png'))])
        write(file,state);print(f'{len(checks)} literal producer-to-store/display checks passed; settled screenshots saved')
    except Exception as error:
        if browser:browser.save_screenshot(str(attempt/'failure.png'))
        state.update(status='FAILED',finished_at_utc=now(),error=str(error));write(file,state);raise
    finally:
        if browser:browser.quit()


if __name__=='__main__':main()
