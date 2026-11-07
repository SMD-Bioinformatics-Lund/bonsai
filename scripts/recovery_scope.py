"""Allow generic failure probes while protecting all original objects."""

from urllib.parse import urlsplit
from account_scope import AccountScope


class RecoveryScope(AccountScope):
    def check(self,method,path,data=None):
        if method=='GET' and urlsplit(path).path=='/samples/summary/manifest':return
        return super().check(method,path,data)
