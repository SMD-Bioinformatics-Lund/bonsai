#!/usr/bin/env python3
"""Exercise the synthetic local-test dataset through the public Bonsai API."""

from __future__ import annotations

import argparse
import json
import os
import time
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from generate.generate_fixtures import SAMPLE_COUNT


TERMINAL_JOB_STATES = {"finished", "failed", "stopped", "canceled"}


def api_request(
    base_url: str,
    path: str,
    *,
    token: str | None = None,
    data: dict[str, Any] | None = None,
    form: dict[str, str] | None = None,
) -> Any:
    """Make a JSON API request and include a useful error body on failure."""
    headers: dict[str, str] = {}
    body: bytes | None = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if form is not None:
        body = urlencode(form).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        headers=headers,
        method="POST" if body is not None else "GET",
    )
    try:
        with urlopen(request, timeout=15) as response:
            return json.load(response)
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"{request.method} {path} returned HTTP {error.code}: {detail}"
        ) from error


def wait_for_job(
    base_url: str, job_id: str, *, timeout: float, label: str
) -> dict[str, Any]:
    """Wait for one Redis job and fail with its worker error when applicable."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = api_request(base_url, f"/job/status/{job_id}")
        if status["status"] in TERMINAL_JOB_STATES:
            if status["status"] != "finished":
                raise RuntimeError(
                    f"{label} job {job_id} ended as {status['status']}: "
                    f"{status.get('error')}"
                )
            if not status.get("result"):
                raise RuntimeError(f"{label} job {job_id} returned an empty result")
            return status
        time.sleep(0.25)
    raise TimeoutError(f"Timed out waiting for {label} job {job_id}")


def validate_samples(samples: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    """Validate fixture counts, analyses, and index references."""
    synthetic = [
        sample
        for sample in samples
        if sample.get("external_sample_id", "").startswith("synthetic_")
    ]
    expected_total = SAMPLE_COUNT * 2
    if len(synthetic) != expected_total:
        raise RuntimeError(
            f"Expected {expected_total} synthetic samples, found {len(synthetic)}"
        )

    tb = sorted(
        (
            sample
            for sample in synthetic
            if sample["external_sample_id"].startswith("synthetic_tb_")
        ),
        key=lambda sample: sample["external_sample_id"],
    )
    sa = sorted(
        (
            sample
            for sample in synthetic
            if sample["external_sample_id"].startswith("synthetic_sa_")
        ),
        key=lambda sample: sample["external_sample_id"],
    )
    if len(tb) != SAMPLE_COUNT or len(sa) != SAMPLE_COUNT:
        raise RuntimeError(
            f"Expected {SAMPLE_COUNT} TB and {SAMPLE_COUNT} SA samples, "
            f"found {len(tb)} and {len(sa)}"
        )

    for sample in synthetic:
        is_saureus = sample["external_sample_id"].startswith("synthetic_sa_")
        if not sample.get("genome_signature") or not sample.get("ska_index"):
            raise RuntimeError(
                f"{sample['external_sample_id']} is missing a MinHash or SKA index reference"
            )
        parsed_types = {
            result["analysis_type"]
            for field in ("qc_result", "species_prediction", "typing_result")
            for result in sample.get(field, [])
            if result.get("status") == "parsed"
        }
        required = {"qc", "species_prediction"}
        if is_saureus:
            required.update({"mlst", "cgmlst"})
        missing = required - parsed_types
        if missing:
            raise RuntimeError(
                f"{sample['external_sample_id']} is missing parsed analyses: "
                f"{', '.join(sorted(missing))}"
            )

    return (
        [sample["sample_id"] for sample in tb],
        [sample["sample_id"] for sample in sa],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--api",
        default=os.environ.get("BONSAI_API", "http://localhost:18001"),
        help="Bonsai API base URL (default: %(default)s)",
    )
    parser.add_argument(
        "--username", default=os.environ.get("BONSAI_USERNAME", "admin")
    )
    parser.add_argument(
        "--password", default=os.environ.get("BONSAI_PASSWORD", "admin123")
    )
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()

    token_response = api_request(
        args.api,
        "/token",
        form={"username": args.username, "password": args.password},
    )
    token = token_response["access_token"]
    response = api_request(
        args.api, f"/samples?limit={SAMPLE_COUNT * 2}", token=token
    )
    tb_ids, sa_ids = validate_samples(response["data"])
    print(
        f"PASS samples: {SAMPLE_COUNT} synthetic TB + {SAMPLE_COUNT} synthetic SA "
        "with expected analyses"
    )

    submitted = api_request(
        args.api,
        f"/samples/{sa_ids[0]}/similar",
        token=token,
        data={"limit": 10, "similarity": 0.5, "cluster": False},
    )
    finished = wait_for_job(
        args.api,
        submitted["id"],
        timeout=args.timeout,
        label="Branchwater multisearch",
    )
    search_result = finished["result"]
    if not isinstance(search_result, dict) or not search_result.get("matches"):
        raise RuntimeError(
            "Branchwater multisearch returned no matches for a synthetic sample"
        )
    print("PASS Branchwater multisearch: similarity search returned matches")

    checks = (
        ("MinHash", "minhash", sa_ids, "average"),
        ("SKA", "ska", tb_ids, "single"),
        ("MLST", "mlst", sa_ids, "MSTree"),
        ("cgMLST", "cgmlst", sa_ids, "MSTree"),
    )
    for label, typing_method, sample_ids, method in checks:
        submitted = api_request(
            args.api,
            f"/cluster/{typing_method}",
            token=token,
            data={"sampleIds": sample_ids, "method": method},
        )
        finished = wait_for_job(
            args.api, submitted["id"], timeout=args.timeout, label=label
        )
        result = finished["result"]
        if not isinstance(result, str) or not result.endswith(";"):
            raise RuntimeError(f"{label} returned an invalid Newick tree: {result!r}")
        print(f"PASS {label}: clustering returned a Newick tree")


if __name__ == "__main__":
    main()
