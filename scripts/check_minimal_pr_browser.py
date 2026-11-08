#!/usr/bin/env python3
"""Exercise isolated candidate JavaScript in Chromium against inert DOM fixtures.

Real installed DataTables/SearchBuilder/Select/Buttons plugins are bundled once.
Only API/basket/notification dependencies are stubbed; no live Bonsai request is
made, and no curation form is submitted. Both baseline and candidate are checked.
"""
import csv
from datetime import datetime, timezone
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import threading
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait

from verify_minimal_prs import ROOT, REPO, snapshot

IDS=['QC-FILTER-EMPTY','SELECTED-FILTER-STALE','VARIANT-SELECT-ALL-INVALID']

# Dependencies not involved in the tested table behavior return generic values.
STUBS='''
window.auditLoad = (source, overrides={}) => {
  const exports = {};
  const noop = () => {};
  const element = class { constructor() { return document.createElement('div'); } };
  const api = {getUserInfo:async()=>({username:'ordinary',roles:['user']}),getSamplesDetails:async()=>[],getGroups:async()=>[]};
  function require(name) {
    if (name in overrides) return overrides[name];
    if (name === 'datatables.net-bs5') return window.auditDataTable;
    if (name === 'jszip') return window.auditJSZip;
    if (name.includes('notification')) return {initToast:noop,initTooltip:noop,throwSmallToast:noop};
    if (name.endsWith('/api')) return {createGroupViewApi:()=>api};
    if (name.endsWith('/User')) return {User:class {isAdmin=false;}};
    if (name.endsWith('/basket-state')) return {BasketState:class {}};
    if (name.endsWith('/samples-basket-counter')) return {SampleBasketCounter:element};
    if (name.endsWith('/sample-basket')) return {BasketComponent:element};
    return {};
  }
  new Function('require','exports',source)(require,exports);
  return exports;
};
'''


def qc_cells(candidate, directory, mode):
    source=snapshot(candidate)
    template='frontend/bonsai_app/blueprints/groups/templates/cell_fmt.html'
    selected=source/template
    if mode=='baseline':
        selected=directory/'baseline-cells.html'
        selected.write_bytes(subprocess.check_output(['git','-C',str(REPO),'show',f'{candidate["base_commit"]}:{template}']))
    code="""import json
from bonsai_app.app import create_app
from flask import render_template_string
app=create_app()
with app.test_request_context():
 template=open('/audit-qc-template.html').read()+'{{ qc_status_renderer(cell) }}'
 print(json.dumps([render_template_string(template,cell={'status':status,'action':'Review','comment':'Generic note'}) for status in ['failed']*4+['passed']*2+['unprocessed']*2]))
"""
    cmd=['docker','run','--rm','--pull','never','--network','none','--user','1000:1000',
         '-v',f'{source}/frontend/bonsai_app:/app/frontend/bonsai_app:ro','-v',f'{selected}:/audit-qc-template.html:ro',
         '-e','PYTHONPATH=/app/frontend','-e','PYTHONDONTWRITEBYTECODE=1',
         '-e','SECRET_KEY=generic-browser-check','--entrypoint','python','bonsai-species-test-frontend','-c',code]
    result=subprocess.run(cmd,capture_output=True,text=True,check=True)
    (directory/f'{mode}-qc-render-command.json').write_text(json.dumps(cmd,indent=2)+'\n')
    return json.loads(result.stdout)


def fixture(kind, cells=None):
    if kind=='VARIANT-SELECT-ALL-INVALID':
        return '<div class="br-content"><input id="curations-input"><span id="selected-variants-counter">0</span><div id="tbprofiler-variant-table"><table id="tb-profiler-variant-tbl"><thead><tr><th><label><input type="checkbox" id="select-all-variants"> Select all rows</label></th></tr></thead><tbody>'+''.join(f'<tr><td><label><input type="checkbox" data-variant-id="row-{n}" data-analysis-id="generic" data-analysis-type="generic"> Generic stored row {n}</label></td></tr>' for n in range(1,4))+'</tbody></table></div></div>'
    cells=cells or ['<td>failed</td>']*4+['<td>passed</td>']*2+['<td>unprocessed</td>']*2
    return '<div id="basket-content"></div><div id="basket-counter-container"></div><table id="sample-table"><thead><tr><th data-column-id="sample_name" data-filterable="true">Record</th><th data-column-id="qc_status" data-filterable="true" data-searchable="false">QC</th></tr></thead><tbody>'+''.join(f'<tr id="generic-{n}"><td>Generic record {n}</td>{cell}</tr>' for n,cell in enumerate(cells,1))+'</tbody></table>'


def run():
    manifest=json.loads((ROOT/'branches.json').read_text())
    selected=[c for c in manifest['candidates'] if c['id'] in IDS]
    for c in selected:snapshot(c)
    assets=ROOT/'browser-assets';assets.mkdir(exist_ok=True)
    cmd=['docker','run','--rm','--pull','never','--network','none','--user','1000:1000','-v',f'{ROOT}:{ROOT}',
         '-v',f'{REPO}/scripts:/audit-scripts:ro','-e','NODE_PATH=/app/frontend/node_modules',
         '--entrypoint','node','bonsai-general-node-tools','/audit-scripts/prepare_minimal_pr_browser.cjs',str(ROOT)]
    subprocess.run(cmd,check=True)
    attempt=ROOT/'browser-checks'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S');attempt.mkdir(parents=True)
    handler=functools.partial(SimpleHTTPRequestHandler,directory=str(assets))
    server=ThreadingHTTPServer(('127.0.0.1',0),handler);threading.Thread(target=server.serve_forever,daemon=True).start()
    options=webdriver.ChromeOptions();options.binary_location='/snap/chromium/current/usr/lib/chromium-browser/chrome'
    options.add_argument('--headless=new');options.add_argument('--window-size=1440,1100');options.add_argument('--disable-background-networking')
    options.add_argument(f'--user-data-dir={attempt/"profile"}')
    downloads=attempt/'downloads';downloads.mkdir()
    options.add_experimental_option('prefs',{'download.default_directory':str(downloads),'download.prompt_for_download':False})
    options.set_capability('goog:loggingPrefs',{'browser':'ALL'})
    browser=webdriver.Chrome(service=Service('/snap/bin/chromium.chromedriver',log_output=str(attempt/'driver.log')),options=options)
    browser.execute_cdp_cmd('Browser.setDownloadBehavior',{'behavior':'allow','downloadPath':str(downloads)})
    wait=WebDriverWait(browser,10);rows=[]
    try:
        for candidate in selected:
            fid=candidate['id'];directory=attempt/fid;directory.mkdir()
            for mode in ['baseline','candidate']:
                cells=qc_cells(candidate,directory,mode) if fid=='QC-FILTER-EMPTY' else None
                page=f'{fid}-{mode}.html'
                (assets/page).write_text('<!doctype html><meta charset="utf-8"><title>' +fid+' / '+mode+'</title><style>body{font:16px sans-serif;padding:24px}table{border-collapse:collapse}td,th{padding:9px;border:1px solid #ccc}button,select{margin:5px;padding:7px}.selected{background:#cde}.dtsb-group{margin:16px}</style><h1>'+fid+' / '+mode+'</h1>'+fixture(fid,cells)+'<script src="foundation.js"></script>')
                browser.get(f'http://127.0.0.1:{server.server_port}/{page}');browser.execute_script('localStorage.clear();'+STUBS)
                def source(label,path):
                    if mode=='candidate':return (assets/f'{fid}-{label}.js').read_text()
                    raw=subprocess.check_output(['git','-C',str(REPO),'show',f'{candidate["base_commit"]}:{path}'],text=True)
                    # Baseline compiled by the same TypeScript installation.
                    invocation=['docker','run','--rm','-i','--pull','never','--network','none','-e','NODE_PATH=/app/frontend/node_modules','--entrypoint','node','bonsai-general-node-tools','-e',"const ts=require('typescript'),fs=require('fs');process.stdout.write(ts.transpileModule(fs.readFileSync(0,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2018,esModuleInterop:true}}).outputText)"]
                    if label=='variants':raw+='\nexport {initVariantSelection};\n'
                    return subprocess.check_output(invocation,input=raw,text=True)
                observed={};checks=[]
                if fid=='VARIANT-SELECT-ALL-INVALID':
                    browser.execute_script('window.auditLoad(arguments[0]).initVariantsView();',source('variants','frontend/web/js/views/variants-table/variants-view.ts'))
                    browser.find_element(By.ID,'select-all-variants').click()
                    payload=json.loads(browser.find_element(By.ID,'curations-input').get_attribute('value'))
                    observed['select_all_payload']=payload
                    checks.append(len(payload)==3 and all(x=={'analysis_id':'generic','analysis_type':'generic','variant_id':f'row-{n}'} for n,x in enumerate(payload,1)))
                    browser.find_element(By.ID,'select-all-variants').click()
                    observed['clear_payload']=json.loads(browser.find_element(By.ID,'curations-input').get_attribute('value'))
                    checks.append(observed['clear_payload']==[])
                    # Clicking a single real row remains supported.
                    browser.find_element(By.CSS_SELECTOR,'input[data-variant-id="row-2"]').click()
                    observed['single_payload']=json.loads(browser.find_element(By.ID,'curations-input').get_attribute('value'))
                    checks.append(observed['single_payload']==[{'analysis_id':'generic','analysis_type':'generic','variant_id':'row-2'}])
                    browser.find_element(By.CSS_SELECTOR,'input[data-variant-id="row-2"]').click()
                    browser.execute_script('new auditDataTable("#tb-profiler-variant-tbl").search("row 2").draw();')
                    browser.find_element(By.ID,'select-all-variants').click()
                    observed['filtered_payload']=json.loads(browser.find_element(By.ID,'curations-input').get_attribute('value'))
                    checks.append(observed['filtered_payload']==[{'analysis_id':'generic','analysis_type':'generic','variant_id':'row-2'}])
                else:
                    controller=source('controller','frontend/web/js/utils/table-controller.ts')
                    browser.execute_script('window.auditController=window.auditLoad(arguments[0]);',controller)
                    if fid=='QC-FILTER-EMPTY':
                        group=source('group','frontend/web/js/views/groups-view/init.ts')
                        result=browser.execute_async_script('const done=arguments[arguments.length-1];const actual=window.auditController;const wrapper={...actual,initSamplesTable:(id,config)=>{const c=actual.initSamplesTable(id,config);window.auditTable=c.getTable();return c;}};window.auditLoad(arguments[0],{"../../utils/table-controller":wrapper}).initGroupView("","","","").then(()=>done("ok")).catch(e=>done(String(e)));',group)
                        assert result=='ok',result
                        wait.until(lambda _:browser.find_elements(By.CSS_SELECTOR,'.dtsb-add'))
                        browser.find_element(By.CSS_SELECTOR,'.dtsb-add').click()
                        Select(browser.find_element(By.CSS_SELECTOR,'.dtsb-data')).select_by_value('1')
                        Select(browser.find_element(By.CSS_SELECTOR,'.dtsb-condition')).select_by_value('=')
                        value=Select(browser.find_element(By.CSS_SELECTOR,'.dtsb-value'))
                        observed['filter_options']=[x.get_attribute('value') for x in value.options]
                        failed=next((option for option in observed['filter_options'] if option.strip()=='failed'),None)
                        assert failed is not None,observed['filter_options']
                        value.select_by_value(failed)
                        observed['filtered_ids']=browser.execute_script('return auditTable.rows({search:"applied"}).ids().toArray();')
                        checks.append(observed['filtered_ids']==[f'generic-{n}' for n in range(1,5)])
                        observed['export_rows']=browser.execute_script('return auditTable.buttons.exportData().body;')
                        checks.append(len(observed['export_rows'])==4)
                        # A second real SearchBuilder criterion must intersect.
                        browser.find_element(By.CSS_SELECTOR,'.dtsb-add').click()
                        Select(browser.find_elements(By.CSS_SELECTOR,'.dtsb-data')[1]).select_by_value('0')
                        Select(browser.find_elements(By.CSS_SELECTOR,'.dtsb-condition')[1]).select_by_value('=')
                        Select(browser.find_elements(By.CSS_SELECTOR,'.dtsb-value')[1]).select_by_value('Generic record 3')
                        observed['combined_ids']=browser.execute_script('return auditTable.rows({search:"applied"}).ids().toArray();')
                        checks.append(observed['combined_ids']==['generic-3'])
                        browser.find_element(By.CSS_SELECTOR,'.dtsb-clearAll').click()
                        observed['after_clear_count']=browser.execute_script('return auditTable.rows({search:"applied"}).count();')
                        checks.append(observed['after_clear_count']==8)
                    else:
                        browser.execute_script('window.auditTable=auditController.initSamplesTable("sample-table",{select:true,layout:{topStart:{buttons:["selectAll","selectNone","showSelected","csv"]}}}).getTable();')
                        browser.find_element(By.CSS_SELECTOR,'#generic-1 td').click()
                        show=next(e for e in browser.find_elements(By.TAG_NAME,'button') if 'Show' in e.text and 'selected' in e.text.lower());show.click()
                        observed['selected_display']=browser.execute_script('return auditTable.rows({search:"applied"}).ids().toArray();')
                        checks.append(observed['selected_display']==['generic-1'])
                        browser.find_element(By.CSS_SELECTOR,'.buttons-select-none').click()
                        observed['after_clear_ids']=browser.execute_script('return auditTable.rows({search:"applied"}).ids().toArray();')
                        checks.append(observed['after_clear_ids']==[])
                        observed['export_rows']=browser.execute_script('return auditTable.buttons.exportData().body;')
                        checks.append(observed['export_rows']==[])
                        before=set(downloads.glob('*.csv'))
                        next(e for e in browser.find_elements(By.TAG_NAME,'button') if e.text.strip()=='CSV').click()
                        wait.until(lambda _:bool(set(downloads.glob('*.csv'))-before))
                        downloaded=(set(downloads.glob('*.csv'))-before).pop()
                        observed['csv_rows']=[row for row in csv.reader(downloaded.read_text(encoding='utf-8-sig').splitlines()) if row]
                        checks.append(len(observed['csv_rows'])==1)
                browser.save_screenshot(str(directory/f'{mode}.png'))
                (directory/f'{mode}.html').write_text(browser.page_source)
                console=browser.get_log('browser');(directory/f'{mode}-console.json').write_text(json.dumps(console,indent=2)+'\n')
                errors=[x for x in console if x['level']=='SEVERE' and 'favicon' not in x['message']]
                record={'id':fid,'head':candidate['head'] if mode=='candidate' else candidate['base_commit'],'mode':mode,
                        'status':'PASS' if all(checks) and not errors else 'FAIL','passed':sum(checks),'total':len(checks),'observed':observed,'console_errors':errors,
                        'live_api_contacted':False,'artifact':str((directory/f'{mode}.png').relative_to(ROOT))}
                rows.append(record);print(f'{fid} {mode}: {record["status"]} {sum(checks)}/{len(checks)}',flush=True)
                (attempt/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
    finally:
        browser.quit();server.shutdown()
    assert len(rows)==6 and all(x['status']=='PASS' if x['mode']=='candidate' else x['status']=='FAIL' for x in rows),rows
    print(attempt/'results.json')


if __name__=='__main__':run()
