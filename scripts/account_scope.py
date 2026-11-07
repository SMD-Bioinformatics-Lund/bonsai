"""Only disposable generic objects may be changed in the account/session pass."""

import re
from urllib.parse import urlsplit

from bounded_scope import BoundedScope, ScopeViolation


class AccountScope(BoundedScope):
    def check(self, method, path, data=None):
        parsed = urlsplit(path)
        if method == "OPTIONS":
            method = "GET"
        if method == "GET" and re.fullmatch(r"/samples/external/[^/]+", parsed.path):
            return
        if method == "GET" and parsed.path == "/samples":
            return
        if method == "DELETE" and re.fullmatch(r"/samples/[^/]+", parsed.path):
            if parsed.path.split("/")[2] in self.samples:
                return
            raise ScopeViolation("Single-record deletion must target a disposable record")
        return super().check(method, path, data)
