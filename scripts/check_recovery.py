"""Generic save/retry probes with mutations limited to disposable fixtures."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import json
from pathlib import Path
from threading import Barrier
from uuid import uuid4

from recovery_scope import RecoveryScope
from bounded_workflows import BoundedApi


class RecoveryChecks:
    def __init__(self,run,phase='baseline'):
        self.run=Path(run).resolve();self.root=self.run/'failure-recovery/2026-11-07';self.phase=phase
        self.scope=RecoveryScope()
        if (self.root/'registry.json').exists():
            saved=json.loads((self.root/'registry.json').read_text())
            for name in ['samples','groups','users']:getattr(self.scope,name).update(saved[name])
        self.admin=BoundedApi(self.scope,self.root)
        if (self.root/'fixtures.json').exists():self.fixtures=json.loads((self.root/'fixtures.json').read_text())

    def log(self,case,ok,expected,observed,browser=None,role='admin'):
        status=('PASS' if ok else 'FAIL') if isinstance(ok,bool) else ok
        artifact=None
        if browser:
            if case.startswith('comment-') and browser.find_elements('id','comment-box'):
                browser.execute_script("document.getElementById('comment-box').scrollIntoView({block:'center'})")
            directory=self.root/'browser'/self.phase/role;directory.mkdir(parents=True,exist_ok=True)
            shot=directory/(case+'.png');browser.save_screenshot(str(shot));shot.with_suffix('.html').write_text(browser.page_source)
            shot.with_suffix('.console.json').write_text(json.dumps(browser.get_log('browser'),indent=2));artifact=str(shot.relative_to(self.run))
        item={'time':datetime.now(timezone.utc).isoformat(),'phase':self.phase,'increment':'failure-recovery-and-integrity','surface':'browser' if browser else 'api','role':role,'case':case,'status':status,'expected':expected,'observed':observed,'artifact':artifact,'url':browser.current_url if browser else None}
        with (self.root/'results.jsonl').open('a') as f:f.write(json.dumps(item)+'\n')
        print(case,status)
        return item

    def prepare(self):
        if (self.root/'fixtures.json').exists():raise ValueError('Preserve the existing manifest')
        records={}
        for name in ['metadata','comments','ui','membership']:
            result=self.admin.request('/samples/',data={'sample_id':'bounded_recovery_'+name,'sample_name':'Disposable recovery '+name})
            records[name]=result['internal_sample_id']
        groups={}
        for name in ['base','extra','editor']:
            groups[name]=self.admin.request('/groups/',data={'group_key':'bounded_recovery_'+name,'display_name':'Disposable recovery '+name,'description':'Original description'})['group_id']
        self.fixtures={'records':records,'groups':groups}
        (self.root/'fixtures.json').write_text(json.dumps(self.fixtures,indent=2)+'\n')
        (self.root/'scope.json').write_text(json.dumps(self.scope.config,indent=2)+'\n')

    def clone(self,client=None):
        original=client or self.admin;copy=object.__new__(BoundedApi)
        copy.scope=original.scope;copy.directory=original.directory;copy.username=original.username;copy.url=original.url;copy.token=original.token;copy.last_status=None
        return copy

    def concurrent(self,requests):
        barrier=Barrier(len(requests))
        def send(item):
            path,data,method=item;c=self.clone();barrier.wait()
            response=c.request(path,data=data,method=method,expected=tuple(range(200,600)))
            return c.last_status,response
        with ThreadPoolExecutor(max_workers=len(requests)) as pool:return list(pool.map(send,requests))

    def api_checks(self):
        self.metadata_checks()
        self.comment_checks()

    def metadata_checks(self):
        sid=self.fixtures['records']['metadata']
        expected=[]
        for round_no in range(5):
            names=[f'{self.phase} independent {round_no} {i}' for i in range(2)];expected+=names
            results=self.concurrent([(f'/samples/{sid}/metadata',[{'fieldname':n,'category':'general','type':'string','value':'generic value'}],'POST') for n in names])
        record=self.admin.request('/samples/'+sid);actual=[m['fieldname'] for m in record['metadata']]
        self.log('concurrent-metadata-retention',set(expected)<=set(actual),'Every successful independent metadata append is retained',{'expected_fields':len(expected),'retained_fields':len(set(expected)&set(actual))})
        name=self.phase+' duplicate field'
        results=self.concurrent([(f'/samples/{sid}/metadata',[{'fieldname':name,'category':'general','type':'string','value':str(i)}],'POST') for i in range(3)])
        self.log('concurrent-metadata-uniqueness',sorted(r[0] for r in results)==[200,409,409],'Concurrent creation of one metadata field has one winner and two clear conflicts',{'statuses':[r[0] for r in results]})
    def comment_checks(self):
        sid=self.fixtures['records']['comments'];messages=[]
        for round_no in range(5):
            texts=[f'{self.phase} concurrent note {round_no} {i}' for i in range(3)];messages+=texts
            self.concurrent([(f'/samples/{sid}/comment',{'username':'admin','comment':text},'POST') for text in texts])
        record=self.admin.request('/samples/'+sid);comments=[c for c in record['comments'] if c['comment'] in messages]
        self.log('concurrent-comment-identities',len(comments)==15 and len({c['id'] for c in comments})==15,'Concurrent comments keep every text and distinct identifiers',{'comments_retained':len(comments),'unique_ids':len({c['id'] for c in comments})})
        key=str(uuid4());text=self.phase+' uncertain response retry';body={'username':'admin','comment':text}
        for _ in range(2):self.admin.request(f'/samples/{sid}/comment',data=body,extra_headers={'Idempotency-Key':key})
        record=self.admin.request('/samples/'+sid);matches=[c for c in record['comments'] if c['comment']==text]
        self.log('comment-retry-once',len(matches)==1,'Replaying the same identified request after an uncertain response creates one comment',{'stored_comments':len(matches)})
        self.admin.request(f'/samples/{sid}/comment',data={'username':'admin','comment':text+' changed'},extra_headers={'Idempotency-Key':key},expected=tuple(range(200,600)))
        self.log('comment-key-content-conflict',self.admin.last_status==409,'A reused request key with changed text gives conflict instead of silently changing intent',{'http_status':self.admin.last_status})
        gid=self.fixtures['groups']['editor']
        self.concurrent([(f'/groups/{gid}',{'display_name':'Recovery '+self.phase},'PUT'),(f'/groups/{gid}',{'description':'Description '+self.phase},'PUT')])
        record=self.admin.request('/groups/'+gid)
        self.log('independent-group-fields',record['display_name']=='Recovery '+self.phase and record['description']=='Description '+self.phase,'Independent partial group updates preserve both fields',{'name_retained':record['display_name']=='Recovery '+self.phase,'description_retained':record['description']=='Description '+self.phase})

    def cleanup(self):
        self.admin=BoundedApi(self.scope,self.root)
        for sid in self.scope.samples:self.admin.request('/samples/',method='DELETE',data=[sid])
        for gid in self.scope.groups:self.admin.request('/groups/'+gid,method='DELETE')
