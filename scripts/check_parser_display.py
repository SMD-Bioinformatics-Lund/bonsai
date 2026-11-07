"""Read-only links from independent frozen-input facts to existing API records."""

from collections import defaultdict
from datetime import datetime,timezone
import json
from pathlib import Path
import csv
import io

from bounded_workflows import BoundedApi
from parser_display_scope import ParserDisplayScope


def at(value,path):
    for part in path:value=value[part]
    return value


class ParserDisplayChecks:
    def __init__(self,run,phase='baseline'):
        self.run=Path(run).resolve();self.root=self.run/'parser-display/2026-11-07';self.phase=phase
        self.scope=ParserDisplayScope();self.api=BoundedApi(self.scope,self.root,'admin','admin123')
        self.catalog=json.loads((self.run/'fixtures/expectations.json').read_text())['samples']
        self.facts=json.loads((self.root/'baseline/input-facts.json').read_text())
        self.parsed=json.loads((self.root/'baseline/parsed.json').read_text())

    def log(self,case,ok,expected,observed,*,sample=None,assay=None,software=None,browser=None,role='admin',screenshot=False):
        status=('PASS' if ok else 'FAIL') if isinstance(ok,bool) else ok
        artifact=None
        if browser and (screenshot or status=='FAIL'):
            directory=self.root/'browser'/self.phase/role;directory.mkdir(parents=True,exist_ok=True)
            path=directory/(case+'-'+str(sample)+'.png');browser.save_screenshot(str(path));path.with_suffix('.html').write_text(browser.page_source)
            path.with_suffix('.console.json').write_text(json.dumps(browser.get_log('browser'),indent=2));artifact=str(path.relative_to(self.run))
        row={'time':datetime.now(timezone.utc).isoformat(),'phase':self.phase,'surface':'browser' if browser else 'api','case':case,'sample':sample,
             'assay':assay,'software':software,'role':role,'status':status,'expected':expected,'observed':observed,'artifact':artifact}
        with (self.root/'results.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
        if status!='PASS':print(case,sample,status)
        return row

    def collect(self):
        rows=self.api.request('/samples/summary',data={'fields':['sample_id','sample_name','external_sample_id'],'limit':0,'offset':0})['data']
        ids={r['external_sample_id']:r['sample_id'] for r in rows};records={}
        for case in self.catalog:records[case['sample_id']]=self.api.request('/samples/'+ids[case['sample_id']])
        (self.root/(self.phase+'-api-records.json')).write_text(json.dumps(records,indent=2)+'\n')
        self.records=records
        return records

    def load(self):
        self.records=json.loads((self.root/'baseline-api-records.json').read_text())

    def api_checks(self):
        self.collect()
        for case in self.catalog:
            sid=case['sample_id'];record=self.records[sid]
            identity={k:record.get(k) for k in ['sample_name','lims_id','external_sample_id']}
            expected={'sample_name':case['sample_name'],'lims_id':case['lims_id'],'external_sample_id':sid}
            self.log('source-record-identity',identity==expected,'Existing record identity equals its frozen manifest',identity,sample=sid,assay=case['assay'])
            stored={(d['software'],d['analysis_type']):d for surface in ['species_prediction','typing_result','qc_result','element_type_result'] for d in record[surface]}
            grouped=defaultdict(list)
            for fact in self.facts[sid]:grouped[(fact['software'],fact['analysis_type'])].append(fact)
            for (software,kind),facts in grouped.items():
                descriptor=stored.get((software,kind))
                if descriptor is None:
                    self.log('literal-fields-'+kind,'N/A' if software=='kleborate' else False,'Selected literal input fields reach the stored API result',
                        {'reason':'No stored counterpart for this frozen report','fields':len(facts),'missing_analysis':kind},sample=sid,assay=case['assay'],software=software)
                    continue
                failures=[]
                for fact in facts:
                    try:actual=at(descriptor['result'],fact['path'])
                    except (KeyError,IndexError,TypeError):actual={'unavailable':True}
                    if actual!=fact['expected']:failures.append({**fact,'actual':actual})
                self.log('literal-fields-'+kind,not failures,'Selected literal input fields reach the stored API result',
                    {'fields_compared':len(facts),'mismatches':failures,'status':descriptor['status']},sample=sid,assay=case['assay'],software=software)
            mismatches=[];missing=[]
            for software,bundle in self.parsed[sid].items():
                for kind,envelope in bundle['results'].items():
                    descriptor=stored.get((software,kind))
                    if descriptor is None:
                        missing.append({'software':software,'analysis_type':kind,'status':envelope['status']});continue
                    if descriptor['software_version']!=bundle['software_version'] or descriptor['status']!=envelope['status']:
                        mismatches.append({'software':software,'analysis_type':kind,'parsed_status':envelope['status'],'stored_status':descriptor['status'],
                                           'parsed_version':bundle['software_version'],'stored_version':descriptor['software_version']})
            self.log('result-status-and-version',not mismatches,'Present stored descriptors preserve parser status and software version',
                {'mismatches':mismatches,'missing_counterparts':missing},sample=sid,assay=case['assay'])
        print('Existing API comparison completed',len(self.records))

    def provenance_checks(self):
        for case in self.catalog:
            sid=case['sample_id'];raw=json.loads((self.run/'fixtures/samples'/sid/'analysis_meta.json').read_text());pipeline=self.records[sid]['pipeline']
            expected={'assay':raw['assay'],'name':raw['pipeline'],'version':raw['version'],'commit':raw['commit'],'configuration_files':raw['configuration_files']}
            definition=pipeline['pipeline_info']['definition'];config=pipeline['pipeline_info']['run_config']
            actual={'assay':pipeline['assay'],'name':definition['name'],'version':definition['version'],'commit':definition['commit'],'configuration_files':config['configuration_files']}
            self.log('pipeline-source-provenance',actual==expected,'Stored pipeline identity and configuration preserve literal frozen metadata',{'expected':expected,'stored':actual},sample=sid,assay=case['assay'])

    def export_literal_values(self):
        for case in self.catalog:
            if case['assay'] not in {'spyogenes','streptococcus'}:continue
            sid=case['sample_id'];record=self.records[sid]
            for fmt,delimiter in [('csv',','),('tsv','\t')]:
                result=self.api.request('/export/'+record['sample_id']+'/lims?fmt='+fmt,expected=(200,422,500))
                if self.api.last_status==422:
                    self.log('export-literal-values-'+fmt,'N/A','Compare literal configured fields when all required source reports exist',
                        {'reason':'Required source report missing; no export file produced','http_status':422},sample=sid,assay=case['assay']);continue
                rows=list(csv.DictReader(io.StringIO(result),delimiter=delimiter)) if self.api.last_status==200 else []
                values={r['parameter_name']:r['parameter_value'] for r in rows}
                expected={'art':case['species'],'mlst':case['mlst']['sequence_type'],'emm':case['emm'] or 'NA'}
                actual={key:values.get(key) for key in expected}
                ok=actual==expected and all(r['sample_id']==case['sample_name'] for r in rows)
                self.log('export-literal-values-'+fmt,ok,'The species, type, empty fallback and record identity match the frozen inputs',
                    {'expected':expected,'actual':actual,'rows':len(rows),'http_status':self.api.last_status},sample=sid,assay=case['assay'])

    def table_summary_fields(self):
        fields=['sample_id','external_sample_id','emm_type','emm_cluster','mlst_sequence_type','bracken_scientific_name','quast_total_length','quast_n50']
        rows=self.api.request('/samples/summary',data={'fields':fields,'limit':0,'offset':0})['data']
        by_id={row['external_sample_id']:row for row in rows}
        for case in self.catalog:
            sid=case['sample_id'];row=by_id[sid]
            expected={'bracken_scientific_name':case['species'],'quast_total_length':case['assembly_length'],'quast_n50':case['n50']}
            if case.get('mlst'):expected['mlst_sequence_type']=int(case['mlst']['sequence_type'])
            if 'emm' in case:
                expected['emm_type']=case['emm']
                if case['emm']:expected['emm_cluster']=next(f['expected'] for f in self.facts[sid] if f['software']=='emmtyper' and f['path']==['emm_cluster'])
            actual={key:row.get(key) for key in expected}
            self.log('table-summary-literal-fields',actual==expected,'Summary-table fields retain the independently recorded source values',{'expected':expected,'actual':actual},sample=sid,assay=case['assay'])
