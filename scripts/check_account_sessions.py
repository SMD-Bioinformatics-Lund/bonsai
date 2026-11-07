"""Generic disposable fixtures and permission/session evidence for the local stack."""

from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from account_scope import AccountScope
from bounded_workflows import BoundedApi


PASSWORD = "SessionTest123"
ROOT_SUFFIX = "account-sessions/2026-11-07"


class SessionChecks:
    def __init__(self, run, phase="baseline"):
        self.run = Path(run).resolve()
        self.root = self.run / ROOT_SUFFIX
        self.phase = phase
        self.scope = AccountScope()
        registry = self.root / "registry.json"
        if registry.exists():
            saved = json.loads(registry.read_text())
            self.scope.samples.update(saved["samples"])
            self.scope.groups.update(saved["groups"])
            self.scope.users.update(saved["users"])
        self.admin = BoundedApi(self.scope, self.root)
        if (self.root / "fixtures.json").exists():
            self.fixtures = json.loads((self.root / "fixtures.json").read_text())

    def log(self, case, status, expected, observed, *, role="admin", surface="api", browser=None):
        if isinstance(status, bool):
            status = "PASS" if status else "FAIL"
        artifact = None
        if browser:
            directory = self.root / "browser" / self.phase / role
            directory.mkdir(parents=True, exist_ok=True)
            shot = directory / (case + ".png")
            browser.save_screenshot(str(shot))
            shot.with_suffix(".html").write_text(browser.page_source)
            shot.with_suffix(".console.json").write_text(json.dumps(browser.get_log("browser"), indent=2))
            artifact = str(shot.relative_to(self.run))
        item = {"time": datetime.now(timezone.utc).isoformat(), "phase": self.phase, "increment": "account-isolation-and-permissions",
            "case": case, "status": status, "expected": expected, "observed": observed, "role": role,
            "surface": surface, "artifact": artifact, "url": browser.current_url if browser else None}
        with (self.root / "results.jsonl").open("a") as handle:
            handle.write(json.dumps(item) + "\n")
        print(case, role, status)
        return item

    def account_data(self, name, roles, *, disabled=False):
        return {"username": name, "first_name": "Disposable", "last_name": "Session test", "email": name + "@example.org",
                "password": "", "roles": roles, "disabled": disabled}

    def change_account(self, name, roles, *, disabled=False):
        return self.admin.request("/users/" + name, method="PUT", data=self.account_data(name, roles, disabled=disabled))

    def new_record(self, suffix, client=None, **extra):
        client = client or self.admin
        return client.request("/samples/", data={"sample_id": "bounded_session_" + suffix,
            "sample_name": "Disposable session " + suffix, **extra}, expected=tuple(range(200, 600)))

    def prepare(self):
        if (self.root / "fixtures.json").exists():
            raise ValueError("Preserve the existing fixture manifest")
        owner, operator = "bounded_session_owner", "bounded_session_operator"
        for name in (owner, operator):
            data = self.account_data(name, ["admin"]);data["password"] = PASSWORD
            self.admin.request("/users/", data=data)
        creator = BoundedApi(self.scope, self.root, owner, PASSWORD)
        group = creator.request("/groups/", data={"group_key": "bounded_session_private", "display_name": "Disposable private session group",
            "visibility": "private", "invited_users": ["user_one"]})
        self.change_account(owner, ["user"])
        public = self.new_record("public")
        private = self.new_record("private", visibility="private")
        member = self.new_record("group_member", groups=[group["group_id"]])
        sid = public["internal_sample_id"]
        self.admin.request("/samples/" + sid + "/metadata", data=[{"fieldname": "Generic marker", "category": "general", "type": "string", "value": "SESSION-TEST-PUBLIC"}])
        self.admin.request("/samples/" + private["internal_sample_id"] + "/metadata", data=[{"fieldname": "Generic private marker", "category": "general", "type": "string", "value": "SESSION-TEST-PRIVATE"}])
        self.fixtures = {"owner": owner, "operator": operator, "private_group": group,
            "public_id": sid, "private_id": private["internal_sample_id"], "group_member_id": member["internal_sample_id"]}
        (self.root / "fixtures.json").write_text(json.dumps(self.fixtures, indent=2) + "\n")

    def clients(self):
        return {name: BoundedApi(self.scope, self.root, name, PASSWORD if name.startswith("bounded_") else
            ("admin123" if name == "admin" else "user123")) for name in ("admin", "user_one", "user_two", "uploader", self.fixtures["owner"])}

    def matrix(self):
        clients = self.clients()
        sid, gid = self.fixtures["public_id"], self.fixtures["private_group"]["group_id"]
        for role, client in clients.items():
            readable = role != "uploader"
            paths = [("record-read", "/samples/" + sid, {200} if readable else {401,403}),
                ("record-legacy-list", "/samples?"+urlencode({"sid":sid,"limit":1}), {200} if readable else {401,403}),
                ("record-export", "/export/" + sid + "/lims", {422} if readable else {401,403}),
                ("user-list", "/users/", {201} if role == "admin" else {401,403}),
                ("private-group-read", "/groups/" + gid, {200} if role in {"admin", "user_one", self.fixtures["owner"]} else {401,403,404})]
            for case, path, expected in paths:
                client.request(path, expected=tuple(range(200,600)))
                self.log(case, client.last_status in expected, "The documented role and private-group access rules are enforced",
                    {"http_status": client.last_status, "expected_statuses": sorted(expected)}, role=role)
            groups = client.request("/groups/", expected=tuple(range(200,600)))
            listed = isinstance(groups, dict) and any(g["group_id"] == gid for g in groups.get("data", []))
            allowed = role in {"admin", "user_one", self.fixtures["owner"]}
            self.log("private-group-list", listed == allowed, "Only an authorized account sees the private group", {"listed": listed}, role=role)
            response = client.request("/samples/summary", data={"fields":["sample_id","external_sample_id"],"limit":0,"offset":0}, expected=tuple(range(200,600)))
            self.log("record-list", client.last_status == (200 if readable else 401), "The API-only write role cannot list records",
                {"http_status":client.last_status},role=role)
            client.request("/samples/" + sid + "/metadata", data=[{"fieldname":"Role note " + role + " " + self.phase,"category":"general","type":"string","value":"generic test"}],expected=tuple(range(200,600)))
            self.log("generic-metadata-update", client.last_status == (200 if readable else 401), "The configured update permission is enforced", {"http_status":client.last_status},role=role)
            data=self.account_data(self.fixtures["operator"],["admin"])
            client.request("/users/"+self.fixtures["operator"],method="PUT",data=data,expected=tuple(range(200,600)))
            self.log("account-update-role",client.last_status==(200 if role=="admin" else 401),"Only an administrator can edit the disposable account",{"http_status":client.last_status},role=role)
        for role in ("user_one","uploader"):
            client=clients[role]
            self.new_record("created_by_"+role+"_"+self.phase,client)
            self.log("record-create-role",client.last_status==(201 if role=="uploader" else 401),"The documented API upload role can create a generic record; an ordinary account cannot",{"http_status":client.last_status},role=role)
        target=self.new_record("single_delete_"+self.phase)["internal_sample_id"]
        clients["user_two"].request("/samples/"+target,method="DELETE",expected=tuple(range(200,600)))
        status=clients["user_two"].last_status
        self.admin.request("/samples/"+target,expected=(200,404))
        self.log("single-delete-denied",status in {401,403} and self.admin.last_status==200,"Both deletion entry points deny ordinary accounts without removing the record",{"delete_status":status,"record_status_after":self.admin.last_status},role="user_two")
        target=self.new_record("bulk_delete_"+self.phase)["internal_sample_id"]
        clients["user_two"].request("/samples/",method="DELETE",data=[target],expected=tuple(range(200,600)))
        self.log("bulk-delete-denied",clients["user_two"].last_status in {401,403},"The bulk deletion route denies an ordinary account",{"http_status":clients["user_two"].last_status},role="user_two")
        self.private_map(clients["user_two"])

    def private_map(self, client):
        sid=self.fixtures["private_id"]
        for case,path in [("private-record-read","/samples/"+sid),("private-record-external-lookup","/samples/external/bounded_session_private"),("private-record-export","/export/"+sid+"/lims")]:
            result=client.request(path,expected=tuple(range(200,600)))
            self.log(case,"N/A","Record-private access policy remains undefined; actual route behavior is recorded",{"http_status":client.last_status,"generic_private_marker_returned":"SESSION-TEST-PRIVATE" in json.dumps(result)},role=client.username)
        response=client.request("/samples/summary",data={"fields":["sample_id","external_sample_id"],"limit":0,"offset":0})
        self.log("private-record-list","N/A","Map the known private-visibility scope gap without inventing an access policy",{"listed":any(x["sample_id"]==sid for x in response["data"])},role=client.username)

    def anonymous(self):
        client=object.__new__(BoundedApi)
        client.scope=self.scope
        client.directory,client.username,client.url,client.token,client.last_status=self.root,'anonymous','http://localhost:18001',None,None
        for case,path,data,method in [
            ('anonymous-record','/samples/'+self.fixtures['public_id'],None,'GET'),
            ('anonymous-list','/samples/summary',{'fields':['sample_id'],'limit':0,'offset':0},'POST'),
            ('anonymous-users','/users/',None,'GET'),
            ('anonymous-group','/groups/'+self.fixtures['private_group']['group_id'],None,'GET'),
            ('anonymous-update','/samples/'+self.fixtures['public_id']+'/metadata',[{'fieldname':'Anonymous note '+self.phase,'type':'string','value':'generic'}],'POST')]:
            client.request(path,data=data,method=method,expected=tuple(range(200,600)))
            self.log(case,client.last_status==401,'An unauthenticated request cannot read or mutate records',{'http_status':client.last_status},role='anonymous')

    def cleanup(self):
        self.admin=BoundedApi(self.scope,self.root)
        for sid in list(self.scope.samples):
            self.admin.request("/samples/"+sid,expected=(200,404))
            if self.admin.last_status==200:
                self.admin.request("/samples/",method="DELETE",data=[sid])
        for gid in self.scope.groups:self.admin.request("/groups/"+gid,method="DELETE",expected=(200,404))
        for name in self.scope.users:self.admin.request("/users/"+name,method="DELETE",expected=(200,404))
