"""Native UI actions with faults restricted to disposable API targets."""

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait,Select
from urllib.parse import urlencode

from check_general_fix_browser import GeneralUI
from check_account_browser import session_cookie_name,expired_cookie


FETCH_FAULTS = """
if(!window.recoveryFetchInstalled){window.recoveryFetchInstalled=true;
window.recoveryFaults=[];window.recoveryHits=[];window.recoveryReleases=[];
const originalFetch=window.fetch.bind(window);
window.fetch=async(input,options={})=>{
 const url=new URL(typeof input==='string'?input:input.url,location.href);
 const method=(options.method||'GET').toUpperCase();
 let rule=window.recoveryFaults.find(r=>r.path===url.pathname&&r.method===method&&r.remaining>0);
 if(rule&&rule.skip>0){rule.skip--;rule=null;}
 if(rule){rule.remaining--;window.recoveryHits.push({path:url.pathname,method});
   if(rule.mode==='before')throw new TypeError('Injected network loss before write');
   if(rule.mode==='hold')await new Promise(resolve=>window.recoveryReleases.push(resolve));
 }
 const response=await originalFetch(input,options);
 if(rule&&rule.mode==='after'){await response.arrayBuffer();throw new TypeError('Injected lost acknowledgement');}
 return response;
};
}
"""


class RecoveryUI(GeneralUI):
    def __init__(self,browser,args,checks,gate):
        self.browser,self.args,self.checks,self.gate=browser,args,checks,gate;self.api=checks.admin;self.wait=WebDriverWait(browser,12)
        browser.execute_cdp_cmd('Network.enable',{})
        browser.execute_cdp_cmd('Network.setBlockedURLs',{'urls':checks.scope.config['browser_blocked_urls']+['*://localhost:18000/*/igv*']})
        previous=getattr(browser,'_recovery_fault_script',None)
        if previous:browser.execute_cdp_cmd('Page.removeScriptToEvaluateOnNewDocument',{'identifier':previous})
        browser._recovery_fault_script=browser.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument',{'source':FETCH_FAULTS})['identifier']

    def log(self,name,ok,expected,observed):return self.checks.log(name,ok,expected,observed,self.browser,self.args.role)

    def fault(self,path,mode,method='PUT',count=1,skip=0):
        assert any(s in path for s in self.checks.scope.groups|self.checks.scope.samples)
        self.browser.execute_script('window.recoveryFaults.push(arguments[0])',{'path':path,'mode':mode,'method':method,'remaining':count,'skip':skip})

    def field(self,ident,value):
        e=self.browser.find_element(By.ID,ident);e.clear();e.send_keys(value)

    def editor(self,gid):
        self.browser.get(self.args.url+'/groups/'+gid+'/edit')
        self.wait.until(EC.presence_of_element_located((By.ID,'group-name')))
        self.browser.execute_script("window.recoverySaves=0;document.querySelector('group-editor').addEventListener('group-editor:saved',()=>window.recoverySaves++)")

    def saved(self):
        self.wait.until(lambda _:'/edit' not in self.browser.current_url or self.browser.execute_script('return window.recoverySaves||0')>0)

    def group_checks(self):
        self.login('admin');gid=self.checks.fixtures['groups']['editor'];path='/groups/'+gid
        self.editor(gid);before=self.api.request(path);name='Blocked save '+self.checks.phase
        self.field('group-name',name);self.fault(path,'before');self.click(self.browser.find_element(By.ID,'ge-save'))
        self.wait.until(lambda _:'Failed to save' in self.browser.find_element(By.TAG_NAME,'body').text or 'could not' in self.browser.find_element(By.TAG_NAME,'body').text.lower())
        saved=self.api.request(path)
        self.log('group-write-blocked',saved['display_name']==before['display_name'] and self.browser.find_element(By.ID,'group-name').get_attribute('value')==name,
            'A write blocked before acceptance keeps the original data and the editable draft',{'stored_unchanged':saved['display_name']==before['display_name'],'draft_retained':self.browser.find_element(By.ID,'group-name').get_attribute('value')==name})
        self.editor(gid);name='Partial save '+self.checks.phase;self.field('group-name',name)
        # Select a different column so the second stage is required.
        selector=self.browser.find_element(By.TAG_NAME,'column-selector')
        show=selector.find_element(By.ID,'show-unselected')
        if not show.is_selected():self.click(show)
        checkbox=selector.find_element(By.CSS_SELECTOR,'.ge-column-checkbox:not(:disabled)');self.click(checkbox)
        self.fault(path+'/allowed_columns','before');self.click(self.browser.find_element(By.ID,'ge-save'))
        self.wait.until(lambda _:'Failed' in self.browser.find_element(By.TAG_NAME,'body').text or 'saved' in self.browser.find_element(By.TAG_NAME,'body').text.lower())
        saved=self.api.request(path);body=self.browser.find_element(By.TAG_NAME,'body').text.lower()
        self.log('group-partial-save-feedback',saved['display_name']==name and any(s in body for s in ['partially','details were saved','some changes']),
            'A failed later stage explicitly explains that earlier group changes were saved',{'core_saved':saved['display_name']==name,'partial_feedback':any(s in body for s in ['partially','details were saved','some changes'])})
        self.click(self.browser.find_element(By.ID,'ge-save'))
        self.saved()
        self.log('group-partial-retry',self.api.request(path)['display_name']==name,'Retrying a known partial save finishes the same group',{'same_group_id':gid in self.browser.current_url})
        self.editor(gid);self.field('group-name','Pending save '+self.checks.phase);self.fault(path,'hold',count=2)
        self.click(self.browser.find_element(By.ID,'ge-save'))
        self.wait.until(lambda _:self.browser.execute_script('return window.recoveryHits.length')>=1)
        save=self.browser.find_element(By.ID,'ge-save');reset=self.browser.find_element(By.ID,'ge-reset')
        guarded=not save.is_enabled() and not reset.is_enabled()
        if save.is_enabled():self.click(save)
        hits=self.browser.execute_script('return window.recoveryHits.length')
        self.log('group-pending-actions',guarded and hits==1,'Pending saves block repeated Save and Reset actions',{'save_disabled':not save.is_enabled(),'reset_disabled':not reset.is_enabled(),'write_attempts':hits})
        self.browser.execute_script('window.recoveryReleases.splice(0).forEach(r=>r())')
        self.saved()
        self.overlapping_edit(gid)

    def overlapping_edit(self,gid):
        path='/groups/'+gid
        self.api.request(path,method='PUT',data={'display_name':'Shared edit baseline','description':'Shared description baseline'})
        self.editor(gid);first=self.browser.current_window_handle
        self.browser.switch_to.new_window('tab');second=self.browser.current_window_handle;self.editor(gid)
        self.browser.switch_to.window(first);name='First tab '+self.checks.phase;self.field('group-name',name);self.click(self.browser.find_element(By.ID,'ge-save'))
        self.saved()
        self.browser.switch_to.window(second);description='Second tab '+self.checks.phase;self.field('group-description',description);self.click(self.browser.find_element(By.ID,'ge-save'))
        self.saved()
        saved=self.api.request(path)
        self.log('group-independent-edits',saved['display_name']==name and saved['description']==description,
            'Saving an independent field in a stale tab preserves the other tab change',{'first_change_retained':saved['display_name']==name,'second_change_retained':saved['description']==description})
        self.editor(gid);self.browser.switch_to.window(first);self.editor(gid)
        self.field('group-description','First same-field '+self.checks.phase);self.click(self.browser.find_element(By.ID,'ge-save'));self.saved()
        self.browser.switch_to.window(second);self.field('group-description','Second same-field '+self.checks.phase);self.click(self.browser.find_element(By.ID,'ge-save'));self.saved()
        saved=self.api.request(path)
        self.log('group-same-field-conflict-policy','N/A','Map same-field overlap without introducing a new versioning contract',{'last_writer_value_retained':saved['description']=='Second same-field '+self.checks.phase,'conflict_prompt_visible':'conflict' in self.browser.execute_script('return document.body.innerText').lower()})
        self.browser.close();self.browser.switch_to.window(first)

    def comment_checks(self,modes=('before','after'),suffix=''):
        self.login('user_one');sid=self.checks.fixtures['records']['ui'];url=self.args.url+'/sample/'+sid
        for mode in modes:
            self.browser.get(url);text=self.checks.phase+' '+mode+' save recovery'+suffix
            self.field('comment-box',text);self.gate.arm('/samples/'+sid+'/comment',mode)
            old=self.browser.find_element(By.TAG_NAME,'body')
            self.click(self.button('Add comment'))
            self.wait.until(EC.staleness_of(old))
            self.wait.until(lambda _:self.browser.execute_script('return document.readyState')=='complete')
            body=self.browser.execute_script('return document.body.innerText')
            draft=self.browser.find_elements(By.ID,'comment-box')
            retained=bool(draft) and draft[0].get_attribute('value')==text
            saved=self.api.request('/samples/'+sid);count=sum(c['comment']==text for c in saved['comments'])
            confirmed=count==1 and not retained and 'Comment added' in body
            self.log('comment-'+mode+'-failure',(retained and '500' not in self.browser.title) or confirmed,
                'An interrupted comment save retains its draft or clearly confirms exactly one saved comment',{'stored_comments':count,'draft_retained':retained,'confirmed':confirmed,'title':self.browser.title})
            if confirmed:
                self.log('comment-'+mode+'-retry',count==1,'A transparent retry confirms exactly one comment',{'stored_comments':count,'automatic_recovery':True})
                continue
            if not retained:
                self.browser.back()
                if not self.browser.find_elements(By.ID,'comment-box'):self.browser.get(url)
                self.field('comment-box',text)
            self.click(self.button('Add comment'))
            self.wait.until(lambda _:self.browser.execute_script('return document.readyState')=='complete' and '/comment' not in self.browser.current_url)
            saved=self.api.request('/samples/'+sid);count=sum(c['comment']==text for c in saved['comments'])
            self.log('comment-'+mode+'-retry',count==1,'Retrying the preserved request creates exactly one comment',{'stored_comments':count})

    def session_and_navigation(self):
        self.login('user_one');sid=self.checks.fixtures['records']['ui'];url=self.args.url+'/sample/'+sid
        self.browser.get(url);text=self.checks.phase+' expired session draft';self.field('comment-box',text)
        cookie_name=session_cookie_name();cookie=expired_cookie('user_one',self.browser.get_cookie(cookie_name)['value'])
        self.browser.add_cookie({'name':cookie_name,'value':cookie,'path':'/','httpOnly':True})
        self.click(self.button('Add comment'))
        self.wait.until(lambda _:'/login' in self.browser.current_url or 'logged out' in self.browser.execute_script('return document.body.innerText').lower())
        saved=self.api.request('/samples/'+sid)
        self.log('expired-session-save-rejected',all(c['comment']!=text for c in saved['comments']) and '500' not in self.browser.title,
                 'A session expiring before submission cannot write and receives sign-in feedback',{'comment_written':any(c['comment']==text for c in saved['comments']),'title':self.browser.title})
        self.log('expired-session-draft-recovery','N/A','Map draft recovery after an expired session without persisting sensitive form data',{'draft_available':bool(self.browser.find_elements(By.ID,'comment-box'))})
        self.login('admin');gid=self.checks.fixtures['groups']['editor'];path='/groups/'+gid
        self.editor(gid);name='Uncertain save '+self.checks.phase;self.field('group-name',name);self.fault(path,'after')
        self.click(self.browser.find_element(By.ID,'ge-save'))
        self.wait.until(lambda _:'Failed' in self.browser.execute_script('return document.body.innerText') or 'could' in self.browser.execute_script('return document.body.innerText').lower())
        saved=self.api.request(path);body=self.browser.execute_script('return document.body.innerText').lower()
        self.log('group-lost-acknowledgement',saved['display_name']==name and any(t in body for t in ['may have','some changes','could not confirm']),
                 'A lost save response explains uncertainty instead of claiming no change',{'stored_change':saved['display_name']==name,'uncertainty_feedback':any(t in body for t in ['may have','some changes','could not confirm'])})
        self.click(self.browser.find_element(By.ID,'ge-save'));self.saved()
        self.log('group-lost-ack-retry',self.api.request(path)['display_name']==name,'A retry updates the same existing group',{'same_group_id':gid in self.browser.current_url})
        self.editor(gid);before=self.api.request(path)['display_name'];self.field('group-name','Navigated away '+self.checks.phase);self.fault(path,'hold')
        self.click(self.browser.find_element(By.ID,'ge-save'))
        self.wait.until(lambda _:self.browser.execute_script('return window.recoveryHits.length')==1)
        self.browser.get(self.args.url+'/groups')
        stored=self.api.request(path)['display_name'];self.editor(gid)
        self.log('navigation-before-write',stored==before and self.browser.find_element(By.ID,'group-name').get_attribute('value')==before,
                 'Navigation before a held request is sent leaves stored data unchanged and reloads the saved value',{'stored_unchanged':stored==before,'reloaded_saved_value':self.browser.find_element(By.ID,'group-name').get_attribute('value')==before})

    def membership_checks(self):
        self.login('admin');ids=[self.checks.fixtures['records'][k] for k in ['ui','membership']];gid=self.checks.fixtures['groups']['base'];extra=self.checks.fixtures['groups']['extra']
        self.api.request('/groups/'+gid+'/samples?'+urlencode({'s':ids},doseq=True),method='PUT')
        self.api.request('/groups/'+extra+'/samples?'+urlencode({'s':[ids[0]]},doseq=True),method='PUT')
        self.overview('bounded_recovery',length='-1');self.wait.until(lambda _:len(self.row_ids())==4)
        for sid in ids:
            cell=self.browser.find_element(By.CSS_SELECTOR,'#sample-table tr[id="'+sid+'"] td')
            ActionChains(self.browser).key_down(Keys.CONTROL).click(cell).key_up(Keys.CONTROL).perform()
        assert len(self.browser.find_elements(By.CSS_SELECTOR,'#sample-table tbody tr.selected'))==2
        self.click(self.button('Add to group'));self.wait.until(lambda _:self.selector()[0].find_element(By.ID,'apply').is_enabled())
        assert self.selected_groups()==[gid],self.selected_groups()
        self.click(self.selector()[0].find_element(By.ID,'clear'));self.fault('/groups/'+gid+'/samples','before',method='DELETE',skip=1)
        self.click(self.selector()[0].find_element(By.ID,'apply'));self.wait.until(lambda _:self.selector()[0].find_element(By.ID,'apply').is_enabled())
        edges=self.memberships(ids);remaining=sum(group==gid for _,group in edges)
        body=self.browser.execute_script('return document.body.innerText').lower()
        self.log('membership-partial-error-visible',remaining==1 and 'could not update group memberships' in body,
                 'A later membership failure is visible and confirmed writes are reflected after resynchronization',{'remaining_target_memberships':remaining,'error_visible':'could not update group memberships' in body})
        self.log('membership-unrelated-preserved',(ids[0],extra) in edges,'Partial membership failures preserve unrelated membership',{'unrelated_membership_retained':(ids[0],extra) in edges})
        # After resynchronization only common memberships are shown. This is an explicit limitation.
        self.click(self.selector()[0].find_element(By.ID,'apply'));self.wait.until(lambda _:self.selector()[0].find_element(By.ID,'apply').is_enabled())
        edges=self.memberships(ids)
        self.log('membership-empty-retry-limitation','N/A','Map whether retrying the reset selection repeats the original removal intent',{'remaining_target_memberships':sum(group==gid for _,group in edges),'selected_groups_after_resync':self.selected_groups()})

    def comment_remove_denial(self):
        self.login('user_one');sid=self.checks.fixtures['records']['ui'];path='/samples/'+sid
        self.browser.get(self.args.url+'/sample/'+sid);before=self.api.request(path)['comments']
        old=self.browser.find_element(By.TAG_NAME,'body')
        controls=self.browser.find_elements(By.CSS_SELECTOR,'#comment-container button[aria-label="Remove"]')
        if not controls:
            self.log('comment-removal-control-permission',True,'The ordinary account is not offered an administrator-only removal action',{'remove_controls':0})
            self.login('admin');self.browser.get(self.args.url+'/sample/'+sid)
            controls=self.browser.find_elements(By.CSS_SELECTOR,'#comment-container button[aria-label="Remove"]')
            self.log('comment-removal-admin-control',bool(controls),'The administrator retains the comment-removal action',{'remove_controls':len(controls)})
            return
        self.click(controls[0])
        self.wait.until(EC.staleness_of(old))
        self.wait.until(lambda _:self.browser.execute_script('return document.readyState')=='complete')
        body=self.browser.execute_script('return document.body.innerText').lower();after=self.api.request(path)['comments']
        self.log('comment-removal-denial-feedback',before==after and 'comment could not be removed' in body and '500' not in self.browser.title,
                 'A denied comment-removal request leaves the record unchanged and shows ordinary permission feedback',{'comments_unchanged':before==after,'feedback_visible':'comment could not be removed' in body,'title':self.browser.title})
