"""Focused generic workflow gaps for the consolidated release review."""

from datetime import datetime,timezone
import csv
import io
import json
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from bounded_workflows import BoundedApi
from check_general_fix_browser import GeneralUI
from recovery_scope import RecoveryScope


class ReleaseGapChecks:
    def __init__(self,run):
        self.run=Path(run).resolve();self.root=self.run/'release-review/2026-11-07';self.scope=RecoveryScope()
        if (self.root/'registry.json').exists():
            saved=json.loads((self.root/'registry.json').read_text())
            for name in ['samples','groups','users']:getattr(self.scope,name).update(saved[name])
        self.api=BoundedApi(self.scope,self.root)
        if (self.root/'fixtures.json').exists():self.fixtures=json.loads((self.root/'fixtures.json').read_text())

    def prepare(self):
        if (self.root/'fixtures.json').exists():raise ValueError('Preserve the completed fixture manifest')
        gid=self.api.request('/groups/',data={'group_key':'bounded_review_exports','display_name':'Release review export cases'})['group_id']
        names=['=1+1','+1+1','-1+1','@SUM(1,1)','Quoted, "label"\nCafé','000123456789012345','<b>Audit literal</b>','Ordinary audit record']
        records=[]
        for i,name in enumerate(names):
            body={'sample_id':f'bounded_review_{i+1:02d}','sample_name':name,'lims_id':'00012345678901234'+str(i),'groups':[gid]}
            response=self.api.request('/samples/',data=body)
            records.append({**body,'internal_id':response['internal_sample_id']})
        self.fixtures={'group_id':gid,'records':records}
        (self.root/'fixtures.json').write_text(json.dumps(self.fixtures,indent=2)+'\n')

    def log(self,case,ok,expected,observed,browser=None,artifact=None):
        status=('PASS' if ok else 'FAIL') if isinstance(ok,bool) else ok
        if browser:
            d=self.root/'browser';d.mkdir(exist_ok=True)
            shot=d/(case+'.png');browser.save_screenshot(str(shot));shot.with_suffix('.html').write_text(browser.page_source)
            shot.with_suffix('.console.json').write_text(json.dumps(browser.get_log('browser'),indent=2));artifact=str(shot.relative_to(self.run))
        row={'time':datetime.now(timezone.utc).isoformat(),'case':case,'status':status,'expected':expected,'observed':observed,'artifact':artifact}
        with (self.root/'results.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
        print(case,status)
        return row

    def cleanup(self):
        for sid in self.scope.samples:self.api.request('/samples/',method='DELETE',data=[sid])
        for gid in self.scope.groups:self.api.request('/groups/'+gid,method='DELETE')


class ReleaseGapUI(GeneralUI):
    def __init__(self,browser,args,checks):
        self.browser,self.args,self.checks,self.api=browser,args,checks,checks.api
        self.wait=WebDriverWait(browser,20)
        browser.execute_cdp_cmd('Network.enable',{})
        browser.execute_cdp_cmd('Network.setBlockedURLs',{'urls':checks.scope.config['browser_blocked_urls']+['*://localhost:18000/*/igv*']})
        browser.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument',{'source':"document.addEventListener('submit',e=>{if(e.target.method.toUpperCase()!=='GET'&&new URL(e.target.action,location.href).pathname!=='/login')e.preventDefault()},true)"})

    def log(self,case,ok,expected,observed):return self.checks.log(case,ok,expected,observed,self.browser)

    def group(self):
        self.browser.get(self.args.url+'/groups/'+self.checks.fixtures['group_id'])
        self.wait.until(lambda _:len(self.row_ids())==len(self.checks.fixtures['records']))

    def download(self,label,suffix):
        directory=self.args.run_dir.resolve()/'browser-results'/self.args.role/self.args.session_name/'downloads'
        directory.mkdir(parents=True,exist_ok=True);before=set(directory.iterdir())
        self.click(self.button(label))
        def ready(_):
            files=[p for p in directory.iterdir() if p not in before and p.suffix==suffix and p.stat().st_size]
            return max(files,key=lambda p:p.stat().st_mtime) if files and not list(directory.glob('*.crdownload')) else False
        return self.wait.until(ready)

    def csv_rows(self,path):return [row for row in csv.reader(io.StringIO(path.read_text(encoding='utf-8-sig'))) if row]

    def exports(self):
        self.login('admin');self.group()
        html_name='<b>Audit literal</b>'
        row=next(r for r in self.checks.fixtures['records'] if r['sample_name']==html_name)
        element=self.browser.find_element(By.ID,row['internal_id'])
        literal=html_name in element.text and not element.find_elements(By.TAG_NAME,'b')
        self.log('overview-name-literal',literal,'A harmless markup-like record name remains literal text',{'literal_text':html_name in element.text,'bold_elements':len(element.find_elements(By.TAG_NAME,'b'))})
        csvfile=self.download('CSV','.csv');rows=self.csv_rows(csvfile)
        header=rows[0];names=[r[header.index('Name')] for r in rows[1:]];lims=[r[header.index('LIMS id')] for r in rows[1:]]
        expected=[r['sample_name'] for r in self.checks.fixtures['records']]
        formulas=[name for name in names if name.startswith(('=','+','-','@'))]
        self.log('csv-formula-like-text',not formulas,'Formula-like input remains inert when CSV is opened as a spreadsheet',{'unprotected_values':formulas,'export_rows':len(names)})
        changed=[{'stored':name,'exported':[v for v in names if name.replace('\n',' ')==v or name==v]} for name in expected if name not in names and "'"+name not in names]
        self.log('csv-record-values',not changed,'Text, quoting, Unicode and identifiers retain their supplied values',{'missing_or_changed_names':changed,'leading_zero_ids_retained':all(r['lims_id'] in lims for r in self.checks.fixtures['records'])})
        target=self.checks.root/'exports';target.mkdir(exist_ok=True);(target/'all-records.csv').write_bytes(csvfile.read_bytes())
        xlsx=self.download('Excel','.xlsx')
        ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        with ZipFile(xlsx) as z:
            sheet=ElementTree.fromstring(z.read('xl/worksheets/sheet1.xml'))
            shared=[]
            if 'xl/sharedStrings.xml' in z.namelist():
                tree=ElementTree.fromstring(z.read('xl/sharedStrings.xml'));shared=[''.join(e.itertext()) for e in tree]
            values=[]
            for cell in sheet.findall('.//m:c',ns):
                text=''.join(cell.itertext())
                if cell.get('t')=='s':text=shared[int(cell.find('m:v',ns).text)]
                values.append({'ref':cell.get('r'),'type':cell.get('t'),'text':text,'formula':cell.find('m:f',ns) is not None})
        formula_cells=[c for c in values if c['formula']]
        self.log('xlsx-formula-like-text',not formula_cells,'Spreadsheet exports encode record names as data cells, not formulas',{'formula_cells':formula_cells})
        numeric_lims=[r['lims_id'] for r in self.checks.fixtures['records']]
        missing=[value for value in numeric_lims if not any(c['text']==value and c['type'] in {'s','inlineStr'} for c in values)]
        self.log('xlsx-leading-zero-identifiers',not missing,'Long leading-zero identifiers remain text cells',{'missing_text_identifiers':missing})
        (target/'all-records.xlsx').write_bytes(xlsx.read_bytes());(target/'xlsx-cells.json').write_text(json.dumps(values,indent=2)+'\n')
        self.click(self.button('Select all'));self.click(self.button('Show only selected'));self.click(self.button('Deselect all'))
        selected=len(self.browser.find_elements(By.CSS_SELECTOR,'#sample-table tbody tr.selected'))
        displayed=self.row_ids()
        self.log('selected-only-after-clear',not displayed and selected==0,'Clearing selection under Show only selected yields no displayed records',{'selected_rows':selected,'displayed_rows':len(displayed),'add_to_basket_disabled':not self.browser.find_element(By.ID,'add-to-basket-btn').is_enabled()})
        stale=self.download('CSV','.csv');stale_rows=self.csv_rows(stale)
        (target/'after-selection-cleared.csv').write_bytes(stale.read_bytes())
        self.log('selected-only-export-after-clear',len(stale_rows)<=1,'Export from an empty selected-only view contains no records',{'selected_rows':selected,'exported_records':max(0,len(stale_rows)-1)})

    def presentation(self):
        groups=self.api.request('/groups/')['data'];populated=max(groups,key=lambda g:g['sample_count'])
        self.browser.get(self.args.url+'/groups/'+populated['group_id']+'/edit')
        self.wait.until(lambda _:self.browser.find_elements(By.ID,'group-name'))
        text=self.browser.find_element(By.CSS_SELECTOR,'.ge-samples').text
        self.log('populated-group-member-message','No samples added yet' not in text,'A populated group editor reflects its saved membership count',{'api_members':populated['sample_count'],'member_section':text})
        for width in [320,390]:
            self.browser.set_window_size(width,900);self.browser.get(self.args.url+'/groups')
            self.wait.until(lambda _:self.browser.find_elements(By.ID,'dt-search-0'))
            size=self.browser.execute_script('return {viewport:innerWidth,page:document.documentElement.scrollWidth}')
            self.log('overview-width-'+str(width),size['page']<=size['viewport'],'The page fits the viewport while the table can scroll internally',size)
        self.browser.set_window_size(1440,1100)

    def readonly_selection_payload(self):
        self.login('user_one')
        rows=self.api.request('/samples/summary',data={'fields':['sample_id','external_sample_id'],'limit':0,'offset':0})['data']
        sid=next(r['sample_id'] for r in rows if r['external_sample_id']=='synthetic_tb_003')
        self.browser.get(self.args.url+'/sample/'+sid+'/resistance/variants')
        header=self.wait.until(lambda _:self.browser.find_element(By.ID,'select-all-variants'))
        self.click(header)
        visible=len(self.browser.find_elements(By.CSS_SELECTOR,'#tb-profiler-variant-tbl tbody input[data-variant-id]'))
        payload=json.loads(self.browser.find_element(By.ID,'curations-input').get_attribute('value'))
        invalid=[r for r in payload if any(r.get(k) in {None,'','undefined'} for k in ['analysis_id','analysis_type','variant_id'])]
        self.log('detail-select-all-payload',len(payload)==visible and not invalid,
                 'Select all produces one valid local identifier per displayed row; no form is submitted',
                 {'visible_rows':visible,'local_payload_records':len(payload),'invalid_records':len(invalid),'submitted':False})
        self.click(header)
