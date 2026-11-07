"""Explicit request boundaries for the diagnostic-software follow-up pass."""

import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit


DEFAULT_SCOPE = Path(__file__).resolve().parents[1] / "docs/local-testing/bounded-scope.json"


class ScopeViolation(ValueError):
    pass


class BoundedScope:
    def __init__(self, path=DEFAULT_SCOPE):
        self.config = json.loads(Path(path).read_text())
        self.samples, self.groups, self.users = set(), set(), set()

    def check(self, method, path, data=None):
        parsed = urlsplit(path)
        path = parsed.path
        if path == "/token" and method == "POST":
            return
        if path == "/samples/summary" and method == "POST":
            return
        if method == "GET" and any(re.fullmatch(pattern, path) for pattern in self.config["api_reads"]):
            return
        prefix = self.config["mutation_prefix"]
        create_field = {"/groups/": "group_key", "/samples/": "sample_id", "/users/": "username"}
        if method == "POST" and path in self.config["api_creates"]:
            if isinstance(data, dict) and str(data.get(create_field[path], "")).startswith(prefix):
                if path == "/samples/" and not set(data.get("groups", [])) <= self.groups:
                    raise ScopeViolation("New records may only join disposable test groups")
                return
        if path == "/samples/" and method == "DELETE" and isinstance(data, list) and data and set(data) <= self.samples:
            return
        if re.fullmatch(r"/samples/[^/]+/(?:metadata|comment(?:/\d+)?|qc_status)", path):
            if path.split("/")[2] in self.samples and method in {"POST", "PUT", "DELETE"}:
                return
        if re.fullmatch(r"/groups/[^/]+(?:/(?:samples|allowed_columns))?", path):
            if path.split("/")[2] in self.groups and method in {"PUT", "DELETE"}:
                if path.endswith("/samples"):
                    samples = parse_qs(parsed.query).get("s", [])
                    if not samples or not set(samples) <= self.samples:
                        raise ScopeViolation("Membership changes must target disposable records")
                return
        if re.fullmatch(r"/users/[^/]+", path):
            if path.split("/")[2] in self.users and method in {"PUT", "DELETE"}:
                return
        raise ScopeViolation(f"Outside the recorded test scope: {method} {path}")

    def register(self, method, path, data, response):
        if method != "POST" or not isinstance(response, dict):
            return
        if path == "/samples/" and response.get("internal_sample_id"):
            self.samples.add(response["internal_sample_id"])
        elif path == "/groups/" and response.get("group_id"):
            self.groups.add(response["group_id"])
        elif path == "/users/":
            self.users.add(data["username"])
