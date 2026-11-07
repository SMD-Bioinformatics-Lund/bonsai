"""Incremental software-only probes for the existing isolated Bonsai instance."""

from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from bounded_scope import BoundedScope


class BoundedApi:
    def __init__(self, scope, directory, username="admin", password="admin123"):
        self.scope, self.directory, self.username = scope, Path(directory), username
        self.url, self.token, self.last_status = "http://localhost:18001", None, None
        response = self.request("/token", body=urlencode({"username": username, "password": password}).encode(),
                                content_type="application/x-www-form-urlencoded")
        self.token = response["access_token"]

    def request(self, path, *, data=None, body=None, method=None, expected=(200, 201), content_type="application/json"):
        method = method or ("POST" if data is not None or body is not None else "GET")
        self.scope.check(method, path, data)
        if data is not None:
            body = json.dumps(data).encode()
        headers = {"Content-Type": content_type}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        try:
            response = urlopen(Request(self.url + path, data=body, headers=headers, method=method), timeout=30)
        except HTTPError as error:
            response = error
        with response:
            self.last_status = response.status
            raw = response.read().decode()
        if path != "/token":
            with (self.directory / "requests.jsonl").open("a") as handle:
                handle.write(json.dumps({"time": datetime.now(timezone.utc).isoformat(), "role": self.username,
                                         "method": method, "path": path, "status": self.last_status}) + "\n")
        allowed = (expected,) if isinstance(expected, int) else expected
        assert self.last_status in allowed, (method, path, self.last_status, raw[:600])
        try:
            result = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            result = raw[:500]
        if self.last_status < 300:
            self.scope.register(method, path, data, result)
            (self.directory / "registry.json").write_text(json.dumps({"samples": sorted(self.scope.samples),
                "groups": sorted(self.scope.groups), "users": sorted(self.scope.users)}, indent=2) + "\n")
        return result


class Results:
    def __init__(self, run, phase="bounded-baseline"):
        self.run = Path(run).resolve()
        self.directory = self.run / "bounded/2026-11-07"
        self.directory.mkdir(parents=True, exist_ok=True)
        self.phase = phase
        self.increment = "record-workflows"

    def check(self, case, ok, expected, observed, *, surface="api", role="admin", sample=None, artifact=None, url=None):
        item = {"time": datetime.now(timezone.utc).isoformat(), "phase": self.phase, "increment": self.increment,
                "surface": surface, "role": role, "case": case, "status": "PASS" if ok else "FAIL",
                "expected": expected, "observed": observed, "sample": sample, "artifact": artifact, "url": url}
        with (self.directory / "results.jsonl").open("a") as handle:
            handle.write(json.dumps(item) + "\n")
        print(case, item["status"])
        return item


def prepare_and_probe(run, phase="bounded-baseline"):
    result = Results(run, phase)
    if (result.directory / "fixtures.json").exists():
        raise ValueError("Preserve the existing fixture manifest; use a fresh run directory for a new preparation")
    scope = BoundedScope()
    admin = BoundedApi(scope, result.directory)
    ordinary = BoundedApi(scope, result.directory, "user_two", "user123")
    existing_groups = admin.request("/groups/")["data"]
    existing_records = admin.request("/samples/summary", data={"fields": ["sample_id", "external_sample_id"], "limit": 0, "offset": 0})["data"]
    if any(g["group_key"].startswith("bounded_") for g in existing_groups) or any(
        row["external_sample_id"].startswith("bounded_") for row in existing_records
    ):
        raise ValueError("Disposable identifiers already exist; inspect their existing registry before starting another run")
    groups = [admin.request("/groups/", data={"group_key": "bounded_" + n,
                "display_name": "Bounded software test " + n}) for n in ("common", "additional")]
    group = groups[0]["group_id"]
    names = ["Bounded plain record", "Bounded Unicode Åäö café", 'Bounded comma, "quoted"', "=1+1", "Bounded multi\nline"]
    samples = []
    for n, name in enumerate(names, 1):
        response = admin.request("/samples/", data={"sample_id": f"bounded_record_{n:03d}", "sample_name": name,
                                 "lims_id": f"000{n:02d}", "groups": [group]})
        samples.append({"sample_id": response["internal_sample_id"], "external_sample_id": f"bounded_record_{n:03d}",
                        "sample_name": name, "lims_id": f"000{n:02d}"})
    private = admin.request("/samples/", data={"sample_id": "bounded_private_record", "sample_name": "Bounded private record",
                            "visibility": "private"})
    fixtures = {"groups": groups, "samples": samples, "private_id": private["internal_sample_id"],
                "owned_samples": sorted(scope.samples), "owned_groups": sorted(scope.groups), "owned_users": []}
    (result.directory / "fixtures.json").write_text(json.dumps(fixtures, indent=2) + "\n")
    sid = samples[0]["sample_id"]

    def probe(label, path, data, expected, description, method=None, client=admin):
        response = client.request(path, data=data, method=method, expected=tuple(range(200, 600)))
        result.check(label, client.last_status in expected, description,
                     {"http_status": client.last_status, "response": response}, role=client.username, sample=sid)
        return response

    pair = {"sample_id": "bounded_pair_first", "sample_name": "Bounded identity pair", "lims_id": "BOUNDED-LIMS",
            "sequencing": {"platform": "illumina", "sequencing_run_id": "bounded-run"}}
    admin.request("/samples/", data=pair)
    pair["sample_id"] = "bounded_pair_second"
    probe("duplicate-lims-run-pair", "/samples/", pair, {409},
          "The supported unique LIMS/run pair is rejected on repeated creation")
    probe("duplicate-group-key", "/groups/", {"group_key": "bounded_common", "display_name": "Duplicate"},
          {409}, "A duplicate group key returns conflict without creating a second group")
    probe("invalid-group-key", "/groups/", {"group_key": "bounded_UPPER", "display_name": "Invalid"},
          {400, 422}, "Invalid group identifiers receive validation feedback")
    metadata = [
        {"fieldname": "Note", "category": "general", "type": "string", "value": 'Quoted, "text" & café\nSecond line'},
        {"fieldname": "Count", "category": "statistics", "type": "integer", "value": 7},
        {"fieldname": "Last note", "category": "general", "type": "string", "value": "Retained"},
        {"fieldname": "Inventory", "category": "general", "type": "table", "value": 'Item,Label\nDesk,"Comma, quote"\nChair,café\n'},
    ]
    probe("metadata-mixed-scalar-table", f"/samples/{sid}/metadata", metadata, {200},
          "Text, Unicode, multiline content and a quoted CSV table can be appended together")
    probe("metadata-duplicate-fields", f"/samples/{sid}/metadata", metadata, {409},
          "Repeating metadata field names returns conflict")
    probe("metadata-invalid-integer", f"/samples/{sid}/metadata",
          [{"fieldname": "Invalid count", "category": "general", "type": "integer", "value": None}], {422},
          "Invalid metadata is rejected as input validation")
    probe("metadata-empty-batch", f"/samples/{sid}/metadata", [], {400, 422},
          "An empty metadata batch is rejected without a server error")
    probe("metadata-malformed-csv", f"/samples/{sid}/metadata",
          [{"fieldname": "Malformed", "category": "general", "type": "table", "value": 'Item,Count\n"unclosed,2'}],
          {400, 422}, "Malformed CSV receives input-validation feedback")

    empty_sid = samples[1]["sample_id"]
    probe("metadata-empty-cell-upload", f"/samples/{empty_sid}/metadata",
          [{"fieldname": "Empty cells", "category": "general", "type": "table", "value": 'Item,Count\nDesk,\nChair,3\n'}],
          {200}, "A valid CSV table may contain an empty cell")
    response = admin.request(f"/samples/{empty_sid}", expected=tuple(range(200, 600)))
    result.check("metadata-empty-cell-read", admin.last_status == 200,
                 "A record remains readable after accepting a CSV table with empty cells",
                 {"http_status": admin.last_status, "response": response if admin.last_status != 200 else response["metadata"]}, sample=empty_sid)

    for path in ["/users/", f"/groups/{group}"]:
        ordinary.request(path, expected=tuple(range(200, 600)))
        expected = {401, 403} if path == "/users/" else {200}
        result.check("role-read-" + ("users" if path == "/users/" else "public-group"), ordinary.last_status in expected,
                     "The ordinary account can read public groups but cannot list other users", {"http_status": ordinary.last_status}, role="user_two")
    probe("role-denies-record-deletion", "/samples/", [sid], {401, 403},
          "An ordinary account cannot delete a record", method="DELETE", client=ordinary)
    if ordinary.last_status == 200:
        replacement = admin.request("/samples/", data={"sample_id": "bounded_record_001", "sample_name": names[0],
                                    "lims_id": "00001", "groups": [group]})
        samples[0]["sample_id"] = replacement["internal_sample_id"]
        admin.request(f'/samples/{samples[0]["sample_id"]}/metadata', data=metadata)
    probe("role-denies-group-deletion", f"/groups/{group}", None, {401, 403},
          "An ordinary account cannot delete an administrator-owned group", method="DELETE", client=ordinary)
    response = ordinary.request(f'/samples/{private["internal_sample_id"]}', expected=tuple(range(200, 600)))
    result.check("private-record-read-access", ordinary.last_status in {401, 403, 404},
                 "A record accepted with private visibility is unavailable to an uninvited account",
                 {"http_status": ordinary.last_status, "returned_visibility": response.get("visibility") if isinstance(response, dict) else None},
                 role="user_two", sample=private["internal_sample_id"])
    fixtures.update(owned_samples=sorted(scope.samples), owned_groups=sorted(scope.groups), owned_users=sorted(scope.users))
    (result.directory / "fixtures.json").write_text(json.dumps(fixtures, indent=2) + "\n")
    return scope, admin, result, fixtures


def retest_record_fixes(run):
    result = Results(run, "bounded-fixed")
    scope = BoundedScope()
    registry = json.loads((result.directory / "registry.json").read_text())
    scope.samples.update(registry["samples"])
    scope.groups.update(registry["groups"])
    scope.users.update(registry["users"])
    admin = BoundedApi(scope, result.directory)
    ordinary = BoundedApi(scope, result.directory, "user_two", "user123")
    fixtures = json.loads((result.directory / "fixtures.json").read_text())
    sid = fixtures["samples"][0]["sample_id"]
    for case, payload in [
        ("metadata-empty-batch", []),
        ("metadata-malformed-csv", [{"fieldname": "Malformed", "type": "table", "value": 'Item,Count\n"unclosed,2'}]),
    ]:
        admin.request(f"/samples/{sid}/metadata", data=payload, expected=(422, 500))
        result.check(case, admin.last_status == 422, "Invalid input is rejected before a write with HTTP 422", {"http_status": admin.last_status}, sample=sid)
    empty_sid = fixtures["samples"][1]["sample_id"]
    response = admin.request("/samples/" + empty_sid, expected=(200, 500))
    result.check("metadata-empty-cell-read", admin.last_status == 200,
                 "Previously accepted empty cells are readable without a database migration",
                 {"http_status": admin.last_status, "metadata": response.get("metadata") if isinstance(response, dict) else None}, sample=empty_sid)
    ordinary.request("/samples/", method="DELETE", data=[sid], expected=(200, 401, 403))
    denied = ordinary.last_status in {401, 403}
    admin.request("/samples/" + sid)
    result.check("role-denies-record-deletion", denied and admin.last_status == 200,
                 "The ordinary account is denied and the record remains available",
                 {"denied": denied, "record_read_status_after": admin.last_status}, role="user_two", sample=sid)
    return scope, admin, result, fixtures
