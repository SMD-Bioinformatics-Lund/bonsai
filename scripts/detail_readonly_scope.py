"""Local action checks for reading existing result pages without editing them."""

import re
from urllib.parse import parse_qs, urlsplit

from bounded_scope import BoundedScope, ScopeViolation


FILTER_FIELDS = {"freq-operator", "min-frequency", "depth-operator", "min-depth",
                 "filter-variant-type", "filter-genes", "filter-who-class",
                 "yeild-resistance", "hide-dismissed"}


class ReadOnlyDetailScope(BoundedScope):
    def check(self, method, path, data=None):
        if method == "OPTIONS":
            return super().check("GET", path, data)
        if method == "GET" or (method == "POST" and urlsplit(path).path in {"/token", "/samples/summary"}):
            return super().check(method, path, data)
        raise ScopeViolation(f"This increment cannot mutate stored records: {method} {urlsplit(path).path}")

    def check_browser(self, method, path, body=""):
        path = urlsplit(path).path
        if method in {"GET", "HEAD"} and not re.search(r"/(?:similar|cluster|tree|igv|resources|pipeline-runs)(?:/|$)", path):
            return
        if method == "POST" and path == "/login":
            return
        if method == "POST" and re.fullmatch(r"/sample/[^/]+/resistance/variants", path):
            if set(parse_qs(body, keep_blank_values=True)) <= FILTER_FIELDS:
                return
        raise ScopeViolation(f"Outside the read-only browser increment: {method} {path}")


FORM_GUARD = """
document.addEventListener('submit', event => {
  const form = event.target;
  if (form.method.toUpperCase() === 'GET') return;
  const path = new URL(form.action, location.href).pathname;
  if (path === '/login') return;
  const fields = Array.from(new FormData(form).keys());
  const allowed = new Set(FILTER_FIELDS);
  if (form.name === 'variant-filter' && fields.every(name => allowed.has(name)) &&
      !event.submitter?.name?.includes('classify')) return;
  event.preventDefault();
  window.readOnlyBlockedSubmissions = (window.readOnlyBlockedSubmissions || 0) + 1;
}, true);
""".replace("FILTER_FIELDS", repr(sorted(FILTER_FIELDS)))
