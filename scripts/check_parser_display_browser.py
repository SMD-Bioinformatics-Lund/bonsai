"""Native read-only checks against independent frozen report expectations."""

import math
import re

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from check_general_fix_browser import GeneralUI
from check_readonly_details import DetailUI


GUARD="""document.addEventListener('submit',e=>{if(e.target.method.toUpperCase()!=='GET'&&new URL(e.target.action,location.href).pathname!=='/login'){e.preventDefault();window.parserBlockedSubmissions=(window.parserBlockedSubmissions||0)+1}},true)"""


class ParserUI(GeneralUI):
    def __init__(self,browser,args,checks):
        self.browser,self.args,self.checks=browser,args,checks;self.api=checks.api;self.scope=checks.scope
        self.wait=WebDriverWait(browser,20);self.root=checks.root;self.requests={};self.phase=checks.phase
        browser.execute_cdp_cmd('Network.enable',{})
        self.blocked_urls=self.scope.config['browser_blocked_urls']+['*://localhost:18000/*/igv*']
        browser.execute_cdp_cmd('Network.setBlockedURLs',{'urls':self.blocked_urls})
        browser.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument',{'source':GUARD})

    audit=DetailUI.audit

    def log(self,case,ok,expected,observed,source,screenshot=False,software=None):
        return self.checks.log(case,ok,expected,observed,sample=source['sample_id'],assay=source['assay'],software=software,
            browser=self.browser,role=self.args.role,screenshot=screenshot)

    def cards(self):
        return self.browser.execute_script("""return [...document.querySelectorAll('.br-main .card')].map(c=>({
          header:(c.querySelector('.card-header')?.innerText||'').trim(),text:c.innerText,
          labels:[...c.querySelectorAll('[title],[aria-label]')].map(e=>(e.getAttribute('title')||'')+' '+(e.getAttribute('aria-label')||'')),
          rows:[...c.querySelectorAll('tbody tr')].map(r=>[...r.querySelectorAll('th,td')].map(e=>e.innerText.trim()))}))""")

    def open(self,case,extended=False):
        sid=case['sample_id'];record=self.checks.records[sid]
        self.browser.get(self.args.url+'/sample/'+record['sample_id']+('?extended=1' if extended else ''))
        self.wait.until(lambda _:self.browser.execute_script('return document.readyState')=='complete')
        return self.cards()

    def sweep(self,sample_ids=None):
        self.login('user_one')
        for case in self.checks.catalog:
            sid=case['sample_id']
            if sample_ids and sid not in sample_ids:continue
            cards=self.open(case);body=self.browser.execute_script('return document.body.innerText')
            rep=sid.endswith(('_001','_002'))
            identity=all(value in body for value in [sid,case['sample_name'],case['lims_id']]) and '500' not in self.browser.title
            self.log('summary-input-identity',identity,'The page preserves all frozen record identifiers',{'identity_matches':identity,'title':self.browser.title},case,screenshot=rep)
            if not identity:continue
            bracken=next((c for c in cards if c['header'].startswith('Species prediction') and 'Bracken' in c['header']),None)
            first=[f for f in self.checks.facts[sid] if f['software']=='bracken' and f['path']==[0,'fraction_total_reads']][0]
            fraction_ok=bool(bracken) and bool(bracken['rows']) and math.isclose(float(bracken['rows'][0][1].rstrip('%')),first['expected']*100,abs_tol=0.005)
            self.log('species-percentage-format',fraction_ok,'A source fraction is displayed as its corresponding percentage',{'source_fraction':first['expected'],'displayed':bracken['rows'][0][1] if bracken and bracken['rows'] else None},case,screenshot=rep)
            for software,title in [('quast','Quast v'),('postalignqc','PostQc Alignment v')]:
                facts=[f for f in self.checks.facts[sid] if f['software']==software and len(f['path'])==1 and isinstance(f['expected'],(int,float))]
                if not facts:continue
                card=next((c for c in cards if c['header'].startswith(title)),None);missing=[]
                rows={r[0].replace(' ','').lower():r[1] for r in card['rows'] if len(r)>=2} if card else {}
                for fact in facts:
                    label=fact['path'][0].replace('_','').lower();actual=rows.get(label)
                    try:matches=math.isclose(float(actual.replace(',','').rstrip('%')),fact['expected'],abs_tol=0.005)
                    except (ValueError,AttributeError):matches=False
                    if not matches:missing.append({'field':fact['path'][0],'expected':fact['expected'],'displayed':actual})
                self.log('qc-numeric-values',not missing,'Every selected scalar QC value is displayed with its source value',
                         {'fields_compared':len(facts),'mismatches':missing},case,screenshot=rep,software=software)
            if case.get('mlst'):
                card=next((c for c in cards if c['header']=='MLST'),None);expected=case['mlst']
                ok=bool(card) and expected['scheme'] in card['text'] and re.search(r'\b'+expected['sequence_type']+r'\b',card['text']) is not None
                self.log('mlst-scheme-and-type',ok,'The frozen scheme and type are visible together',{'card_present':bool(card),'expected':expected},case,screenshot=rep)
            if 'emm' in case:
                card=next((c for c in cards if c['header'].startswith('EMMtyper')),None)
                expected=case['emm'];ok=bool(card) and (expected in card['text'] if expected else any(t in card['text'].lower() for t in ['no result','no findings','empty']))
                self.log('emm-summary-display',ok,'A stored EMM result has a reading surface, including explicit empty feedback',{'expected':expected,'card_present':bool(card)},case,screenshot=rep)
            for key,label in [('spa','spatyper'),('sccmec','sccmec')]:
                if key not in case:continue
                present=any(label in c['header'].lower() for c in cards)
                self.log('unsupported-'+key+'-surface','N/A','Map a stored result whose intended frontend support is unresolved',{'expected':case[key],'card_present':present},case,screenshot=rep)
            dbs=self.checks.records[sid]['pipeline']['pipeline_info']['databases'] if self.checks.records[sid].get('pipeline') else []
            # Stored metadata is used only to identify the displayed version control. Source parity is checked separately.
            labels=' '.join(label for c in cards for label in c['labels'])
            truncated=[d['version'] for d in dbs if d.get('version') and d['version'] not in body and d['version'] not in labels]
            self.log('database-version-display',not truncated,'Full stored database versions remain available in visible text or an accessible label',{'missing_full_versions':truncated},case,screenshot=rep)
            if rep:
                extended=self.open(case,True);bracken=next((c for c in extended if c['header'].startswith('Species prediction') and 'Bracken' in c['header']),None)
                facts=[f for f in self.checks.facts[sid] if f['software']=='bracken' and f['path'][-1]=='scientific_name']
                names=[f['expected'] for f in facts]
                self.log('extended-species-row-retention',bool(bracken) and all(n in bracken['text'] for n in names),'The extended view retains both frozen source rows',{'expected_rows':len(names),'displayed_rows':len(bracken['rows']) if bracken else 0},case,screenshot=True)
            self.audit()
        print('Parser display summary sweep completed')
