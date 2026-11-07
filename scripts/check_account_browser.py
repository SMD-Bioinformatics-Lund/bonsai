"""Interactive account-switching and stale-session checks on disposable fixtures."""

import base64
import json
import re
import subprocess

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from check_general_fix_browser import GeneralUI
from check_account_sessions import PASSWORD


def session_cookie_name():
    code="from bonsai_app.app import create_app;print(create_app().config['SESSION_COOKIE_NAME'])"
    return subprocess.check_output(['docker','exec','bonsai-species-test-frontend-1','python','-c',code],stderr=subprocess.PIPE).decode().strip()


def expired_cookie(username, existing_cookie):
    token_code = "from bonsai_api.auth import create_access_token;from datetime import timedelta;print(create_access_token({'sub':" + repr(username) + "},expires_delta=timedelta(seconds=-60)))"
    token = subprocess.check_output(['docker','exec','bonsai-species-test-api-1','python','-c',token_code],stderr=subprocess.PIPE).decode().strip()
    cookie_code = "import sys,json;from bonsai_app.app import create_app;a=create_app();d=json.load(sys.stdin);s=a.session_interface.get_signing_serializer(a);state=s.loads(d['cookie']);state['access_token']=d['token'];print(s.dumps(state))"
    result = subprocess.run(['docker','exec','-i','bonsai-species-test-frontend-1','python','-c',cookie_code],
        input=json.dumps({'cookie':existing_cookie,'token':token}),text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
    return result.stdout.strip()


class AccountUI(GeneralUI):
    def __init__(self,browser,args,checks):
        self.browser,self.args,self.checks=browser,args,checks
        self.api=checks.admin
        self.wait=WebDriverWait(browser,15)
        browser.execute_cdp_cmd('Network.enable',{})
        browser.execute_cdp_cmd('Network.setBlockedURLs',{'urls':checks.scope.config['browser_blocked_urls']+['*://localhost:18000/*/igv*']})
        owned=list(checks.scope.users)
        guard="""document.addEventListener('submit', e=>{
          const path=new URL(e.target.action,location.href).pathname;
          if(e.target.method.toUpperCase()==='GET'||path==='/login')return;
          if(OWNED.some(name=>path==='/admin/users/'+name))return;
          e.preventDefault();window.accountTestBlockedSubmissions=(window.accountTestBlockedSubmissions||0)+1;
        },true);""".replace('OWNED',json.dumps(owned))
        browser.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument',{'source':guard})

    def login(self,role,password=None):
        super().login(role,password or (PASSWORD if role.startswith('bounded_') else None))

    def log(self,case,ok,expected,observed,role=None):
        return self.checks.log(case,ok,expected,observed,role=role or self.args.role,surface='browser',browser=self.browser)

    def subject(self):
        tokens=re.findall(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+',self.browser.page_source)
        for token in tokens:
            try:return json.loads(base64.urlsafe_b64decode(token.split('.')[1]+'==='))['sub']
            except (ValueError,KeyError):pass
        return None

    def open_basket(self):
        if not self.browser.find_element(By.ID,'basket-offcanvas').is_displayed():
            self.click(self.browser.find_element(By.ID,'open-basket-btn'))
        self.wait.until(lambda _: self.browser.find_element(By.ID,'basket-offcanvas').is_displayed())
        self.wait.until(lambda _: 'Loading basket' not in self.browser.find_element(By.ID,'basket-content').text)

    def close_basket(self):
        panel=self.browser.find_element(By.ID,'basket-offcanvas')
        if panel.is_displayed():
            self.click(panel.find_element(By.CSS_SELECTOR,'[data-bs-dismiss="offcanvas"]'))
            self.wait.until(lambda _: not panel.is_displayed())

    def basket_ids(self):
        return [e.get_attribute('id') for e in self.browser.find_elements(By.CSS_SELECTOR,'#basket-content h6')]

    def clear_basket(self):
        self.open_basket()
        self.click(self.browser.find_element(By.ID,'clear-basket-btn'))
        self.wait.until(lambda _: not self.basket_ids())
        self.close_basket()

    def add_public(self):
        self.overview('bounded_session_public')
        self.wait.until(lambda _: self.row_ids()==[self.checks.fixtures['public_id']])
        self.click(self.button('Select all'))
        self.click(self.browser.find_element(By.ID,'add-to-basket-btn'))
        self.open_basket()
        self.wait.until(lambda _: self.basket_ids()==[self.checks.fixtures['public_id']])
        self.close_basket()

    def shared_basket(self):
        self.login('user_one');self.clear_basket();self.add_public()
        self.browser.refresh();self.open_basket()
        self.log('basket-same-account-reload',self.basket_ids()==[self.checks.fixtures['public_id']],
            'Reloading retains the current account selection',{'basket_records':len(self.basket_ids())})
        self.close_basket()
        self.browser.get(self.args.url+'/logout')
        self.log('logout-page-has-no-token',self.subject() is None,'The logged-out page contains no rendered access token',{'rendered_subject':self.subject()},'user_one')
        self.login('user_two');self.open_basket()
        self.log('basket-account-separation',not self.basket_ids(),'The next account has its own empty selection',{'basket_records':len(self.basket_ids())})
        self.click(self.browser.find_element(By.ID,'clear-basket-btn'));self.close_basket()
        self.login('user_one');self.open_basket()
        self.log('basket-other-account-clear',self.basket_ids()==[self.checks.fixtures['public_id']],
            'Clearing another account basket does not clear this account selection',{'basket_records':len(self.basket_ids())})
        self.close_basket()

    def tabs(self):
        self.login('user_one')
        original=self.browser.current_window_handle
        self.browser.switch_to.new_window('tab')
        second=self.browser.current_window_handle
        self.login('user_two')
        self.browser.switch_to.window(original)
        try:WebDriverWait(self.browser,3).until(lambda _:self.subject()!='user_one')
        except TimeoutException:pass
        self.log('other-tab-account-switch',self.subject()!='user_one',
            'An old tab no longer keeps the previous account token after another tab switches accounts',{'rendered_subject':self.subject()},'user_two')
        self.browser.switch_to.window(second);self.browser.close();self.browser.switch_to.window(original)
        self.login('user_one');self.clear_basket();self.add_public()
        self.browser.switch_to.new_window('tab');second=self.browser.current_window_handle
        self.browser.get(self.args.url+'/groups');self.clear_basket()
        self.browser.switch_to.window(original);self.open_basket()
        try:WebDriverWait(self.browser,3).until(lambda _:not self.basket_ids())
        except TimeoutException:pass
        self.log('same-account-tab-selection-sync',not self.basket_ids(),'A basket clear in another tab is reflected here without a page reload',{'basket_records':len(self.basket_ids())},'user_one')
        self.close_basket()
        self.browser.switch_to.window(second);self.browser.get(self.args.url+'/logout')
        self.browser.switch_to.window(original)
        try:WebDriverWait(self.browser,3).until(lambda _:self.subject() is None)
        except TimeoutException:pass
        self.log('other-tab-logout',self.subject() is None,'Logging out in another tab clears the old authenticated page',{'rendered_subject':self.subject()},'user_one')
        self.browser.switch_to.window(second);self.browser.close();self.browser.switch_to.window(original)

    def group_reads(self):
        gid=self.checks.fixtures['private_group']['group_id']
        for role,allowed in [('admin',True),(self.checks.fixtures['owner'],True),('user_one',True),('user_two',False)]:
            self.login(role);self.browser.get(self.args.url+'/groups/'+gid)
            opened='Disposable private session group' in self.browser.find_element(By.TAG_NAME,'body').text
            self.log('private-group-page',opened==allowed and '500' not in self.browser.title,
                'Owner, invitee and admin can open the private group; an uninvited account is denied',{'opened':opened,'title':self.browser.title},role)
        sid=self.checks.fixtures['private_id']
        self.browser.get(self.args.url+'/sample/'+sid+'/metadata')
        body=self.browser.find_element(By.TAG_NAME,'body').text
        self.log('private-record-ui-map','N/A','Map the unfinished record-private policy without changing it',{'generic_private_marker_visible':'SESSION-TEST-PRIVATE' in body},'user_two')

    def lifecycle(self):
        name=self.checks.fixtures['operator']
        self.checks.change_account(name,['admin'])
        self.login(name);self.browser.get(self.args.url+'/admin/users/'+name)
        self.checks.change_account(name,['user'])
        save=self.browser.find_elements(By.CSS_SELECTOR,'button[type="submit"],input[type="submit"]')
        if save:self.click(next(e for e in save if e.is_displayed()))
        self.log('stale-admin-form-role-change','/admin/' not in self.browser.current_url and '500' not in self.browser.title,
            'A form opened before role removal cannot submit an administrator action',{'url_path':self.browser.current_url.split(':18000')[-1],'title':self.browser.title},name)
        self.checks.change_account(name,['user'])
        self.login(name);self.checks.change_account(name,['user'],disabled=True)
        self.browser.get(self.args.url+'/groups')
        self.log('disabled-session-feedback','500' not in self.browser.title and self.subject() is None,
            'Disabling a signed-in account ends its browser session without a server error',{'title':self.browser.title,'rendered_subject':self.subject()},name)
        self.browser.delete_all_cookies()
        self.browser.get(self.args.url+'/login')
        self.browser.find_element(By.ID,'username').send_keys(name,Keys.TAB,PASSWORD,Keys.RETURN)
        body=self.browser.find_element(By.TAG_NAME,'body').text
        self.log('disabled-login-feedback','internal error' not in body.lower() and self.subject() is None,
            'A disabled account receives useful sign-in feedback without an internal-error message',{'internal_error_message':'internal error' in body.lower(),'rendered_subject':self.subject()},name)
        self.checks.change_account(name,['user'])
        self.login(name)
        cookie_name=session_cookie_name()
        cookie=expired_cookie(name,self.browser.get_cookie(cookie_name)['value'])
        self.browser.get(self.args.url+'/login')
        self.browser.add_cookie({'name':cookie_name,'value':cookie,'path':'/','httpOnly':True})
        self.browser.get(self.args.url+'/groups')
        self.log('expired-session-feedback','You have been logged out' in self.browser.find_element(By.TAG_NAME,'body').text,
            'An authentic expired token reaches the logged-out page without a server error',{'title':self.browser.title},name)

    def logout_history(self):
        self.login('user_one');self.browser.get(self.args.url+'/logout');self.browser.back()
        self.log('logout-browser-back',self.subject() is None,'Browser Back after logout does not restore the old authenticated page',{'rendered_subject':self.subject()},'user_one')

    def deleted_account(self):
        name=self.checks.fixtures['operator']
        self.checks.change_account(name,['user']);self.login(name)
        self.checks.admin.request('/users/'+name,method='DELETE')
        self.browser.get(self.args.url+'/groups')
        self.log('deleted-account-session','500' not in self.browser.title and self.subject() is None,
            'An existing session for a deleted disposable account is rejected clearly',{'title':self.browser.title},name)
        data=self.checks.account_data(name,['admin']);data['password']=PASSWORD
        self.checks.admin.request('/users/',data=data)

    def literal_name(self):
        extra=json.loads((self.checks.root/'additional-fixtures.json').read_text())
        self.login('user_one');self.clear_basket();self.overview('bounded_session_markup')
        self.wait.until(lambda _:self.row_ids()==[extra['markup_id']])
        self.click(self.button('Select all'));self.click(self.browser.find_element(By.ID,'add-to-basket-btn'));self.open_basket()
        self.wait.until(lambda _:extra['markup_id'] in self.basket_ids())
        text=self.browser.find_element(By.ID,'basket-content').get_property('textContent')
        self.log('basket-literal-record-name','Session <b>literal name</b>' in text and not self.browser.find_elements(By.CSS_SELECTOR,'#basket-content h6 b'),
            'A generic record name is displayed literally rather than interpreted as HTML',{'literal_name_displayed':'Session <b>literal name</b>' in text,'parsed_name_tags':len(self.browser.find_elements(By.CSS_SELECTOR,'#basket-content h6 b'))})
        self.close_basket()

    def isolated_profile(self):
        from copy import copy
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        self.login('user_one');self.clear_basket();self.add_public()
        options=webdriver.ChromeOptions();options.binary_location='/snap/chromium/current/usr/lib/chromium-browser/chrome'
        options.add_argument('--headless=new');options.add_argument('--window-size=1440,1100')
        directory=self.checks.root/'isolated-profile'/self.checks.phase;directory.mkdir(parents=True,exist_ok=True)
        options.add_argument('--user-data-dir='+str(directory))
        options.set_capability('goog:loggingPrefs',{'browser':'ALL'})
        other=webdriver.Chrome(service=Service('/snap/bin/chromium.chromedriver',log_output=str(directory/'chromedriver.log')),options=options)
        try:
            other_args=copy(self.args);second=AccountUI(other,other_args,self.checks)
            second.login('user_two');second.open_basket()
            second.log('isolated-profile-account',not second.basket_ids(),'A separate browser profile starts with its own selection',{'basket_records':len(second.basket_ids())},'user_two')
            second.close_basket();second.login('user_one');second.open_basket()
            second.log('isolated-profile-same-account',not second.basket_ids(),'Browser-local basket state is isolated between profiles even for the same account',{'basket_records':len(second.basket_ids())},'user_one')
            other.get(self.args.url+'/logout');self.browser.refresh()
            self.log('isolated-profile-logout',self.subject()=='user_one','Logout in a separate profile does not end this profile session',{'rendered_subject':self.subject()},'user_one')
        finally:other.quit()
