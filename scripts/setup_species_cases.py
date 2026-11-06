#!/usr/bin/env python3
"""Prepare failed-QC examples and exercise deferred species-specific ingestion."""

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--api", default="http://localhost:18001")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="admin123")
    args = parser.parse_args()
    fixtures = args.run_dir.resolve() / "fixtures"
    sys.path.insert(0, str(fixtures))
    spec = importlib.util.spec_from_file_location("fixture_api", fixtures / "scenario_test.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    api = helper.Api(args.api, args.username, args.password)
    expected = json.loads((fixtures / "expectations.json").read_text())
    samples = api.request("/samples?limit=0")["data"]
    by_external = {item["external_sample_id"]: item for item in samples}
    results = []
    seeded = []
    failures = []
    for case in expected["samples"]:
        sample = by_external.get(case["sample_id"])
        if sample is None:
            failures.append({"case": "seeded-sample", "sample": case["sample_id"], "status": "FAIL", "observed": "Missing sample"})
            continue
        seeded.append({"sample_id": case["sample_id"], "internal_id": sample["sample_id"],
                       "assay": case["assay"]})
        if case["sample_id"].endswith("_010"):
            failed = {"status": "failed", "action": "resequence", "comment": "Synthetic QC follow-up; distinct from general comments"}
            api.request(f"/samples/{sample['sample_id']}/qc_status", method="PUT", data=failed)
            actual = api.sample(sample["sample_id"])["qc_status"]
            assert actual == failed, (case["sample_id"], actual)
            results.append({"case": "failed-qc-setup", "sample": case["sample_id"], "status": "PASS", "qc": actual})
        # A positive and a no-AMR example for both legacy and pipeline Klebsiella paths.
        if case["deferred_analyses"] and case["sample_id"].endswith(("_001", "_002")):
            for item in case["deferred_analyses"]:
                try:
                    api.upload(sample["sample_id"], item["software"], fixtures / "samples" / case["sample_id"] / item["uri"],
                               item["software_version"])
                except Exception as error:
                    failure = {"case": "kleborate-ingestion", "sample": case["sample_id"], "status": "FAIL",
                               "expected": "Valid Kleborate report accepted with species-specific results available",
                               "observed": str(error)}
                    results.append(failure)
                    failures.append(failure)
                else:
                    results.append({"case": "kleborate-ingestion", "sample": case["sample_id"], "status": "PASS"})
    artifact = {"time": datetime.now(timezone.utc).isoformat(), "api": args.api,
                "seeded_samples": seeded, "results": results, "failures": failures}
    destination = args.run_dir / "species-setup-results.json"
    destination.write_text(json.dumps(artifact, indent=2) + "\n")
    print(f"Verified {len(seeded)} seeded samples; prepared {sum(row['case'] == 'failed-qc-setup' for row in results)} failed-QC cases")
    for failure in failures:
        print(json.dumps(failure))
    print(destination)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
