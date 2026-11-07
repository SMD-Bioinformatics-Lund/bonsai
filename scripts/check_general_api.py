#!/usr/bin/env python3
"""Small API probes for generic record/group administration, without analyses."""

import json
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4


class Api:
    def __init__(self, url="http://localhost:18001", username="admin", password="admin123"):
        self.url, self.token = url.rstrip("/"), None
        self.token = self.request("/token", body=urlencode({"username": username, "password": password}).encode(),
                                  content_type="application/x-www-form-urlencoded")["access_token"]

    def request(self, path, *, data=None, body=None, method=None, expected=(200, 201), content_type="application/json"):
        if data is not None:
            body = json.dumps(data).encode()
        headers = {"Content-Type": content_type}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = Request(self.url + path, data=body, method=method or ("POST" if body is not None else "GET"), headers=headers)
        try:
            response = urlopen(request, timeout=30)
        except HTTPError as error:
            response = error
        with response:
            payload = response.read().decode()
            statuses = (expected,) if isinstance(expected, int) else expected
            assert response.status in statuses, (request.method, path, response.status, payload[:1500])
        return json.loads(payload) if payload else None


def probe_group_deletion(api, label):
    """Delete one group and check that the other membership survives."""
    suffix = uuid4().hex[:8]
    groups = [api.request("/groups/", data={"group_key": f"delete_{suffix}_{n}",
               "display_name": f"Generic deletion {label} {n}"}) for n in (1, 2)]
    gids = [group["group_id"] for group in groups]
    record = api.request("/samples/", data={"sample_id": f"general_delete_{suffix}",
                         "sample_name": "Generic deletion control", "groups": gids})
    sid = record["internal_sample_id"]
    queried = api.request("/memberships?" + urlencode({"g": gids[0]}))
    before = api.request("/memberships?" + urlencode({"s": sid}))
    api.request(f"/groups/{gids[0]}", method="DELETE")
    after = api.request("/memberships?" + urlencode({"s": sid}))
    result = {"phase": label, "sample_id": sid, "deleted_group": gids[0], "retained_group": gids[1],
              "query_by_deleted_group": queried, "before": before, "after": after,
              "passed": {x["group_id"] for x in after} == {gids[1]}}
    # Remove only this probe's disposable record and remaining group.
    api.request("/samples/", method="DELETE", data=[sid])
    api.request(f"/groups/{gids[1]}", method="DELETE")
    return result
