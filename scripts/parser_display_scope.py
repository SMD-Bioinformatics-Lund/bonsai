"""Read-only API/browser boundary for frozen report fidelity checks."""

from urllib.parse import urlsplit
from detail_readonly_scope import ReadOnlyDetailScope
from bounded_scope import ScopeViolation


class ParserDisplayScope(ReadOnlyDetailScope):
    def check(self, method, path, data=None):
        if method in {'GET', 'OPTIONS'} and urlsplit(path).path == '/samples/summary/manifest':
            return
        return super().check(method, path, data)

    def check_browser(self, method, path, body=''):
        if method == 'POST' and urlsplit(path).path != '/login':
            raise ScopeViolation('Parser display checks cannot submit stored-result changes or filters')
        return super().check_browser(method, path, body)
