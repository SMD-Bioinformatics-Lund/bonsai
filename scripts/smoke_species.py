#!/usr/bin/env python3
"""Check live clustering for every prepared assay using eligible samples."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import re
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--api", default="http://localhost:18001")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="admin123")
    parser.add_argument("--timeout", type=float, default=60)
    args = parser.parse_args()
    root = args.run_dir.resolve()
    fixtures = root / "fixtures"
    sys.path.insert(0, str(fixtures))
    spec = importlib.util.spec_from_file_location("fixture_smoke", fixtures / "smoke_test.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    token = helper.api_request(args.api, "/token", form={"username": args.username, "password": args.password})["access_token"]
    samples = helper.api_request(args.api, "/samples?limit=0", token=token)["data"]
    by_external = {sample["external_sample_id"]: sample for sample in samples}
    expected = json.loads((fixtures / "expectations.json").read_text())
    output = root / "api-trees"
    output.mkdir(exist_ok=True)
    results = []
    for assay in dict.fromkeys(sample["assay"] for sample in expected["samples"]):
        cases = [sample for sample in expected["samples"] if sample["assay"] == assay]
        present = [by_external[sample["sample_id"]] for sample in cases]
        # Failed QC intentionally excludes signatures. Keep those cases available
        # for the UI error-path pass while testing valid clustering separately.
        eligible = [sample for sample in present if sample["qc_status"]["status"] != "failed"]
        ids = [sample["sample_id"] for sample in eligible]
        assert len(ids) >= 2, (assay, "Insufficient eligible samples")
        methods = [("minhash", "average"), ("ska", "single")]
        if cases[0]["mlst"]:
            methods.append(("mlst", "MSTree"))
        if cases[0]["cgmlst"]:
            methods.append(("cgmlst", "MSTree"))
        for method, strategy in methods:
            result = {"assay": assay, "method": method, "strategy": strategy,
                      "selected_ids": ids, "excluded_failed_qc": len(present) - len(ids)}
            try:
                job = helper.api_request(args.api, f"/cluster/{method}", token=token,
                                         data={"sampleIds": ids, "method": strategy})
                result["job_id"] = job["id"]
                completed = helper.wait_for_job(args.api, job["id"], timeout=args.timeout, label=f"{assay}/{method}")
                tree = completed["result"]
                assert isinstance(tree, str) and tree.rstrip().endswith(";"), "Invalid Newick result"
                leaves = re.findall(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", tree)
                assert Counter(leaves) == Counter(ids), ("Incorrect leaf set", leaves)
                destination = output / f"{assay}-{method}.nwk"
                destination.write_text(tree + "\n")
                result.update(status="PASS", tree=str(destination.relative_to(root)))
            except Exception as error:
                result.update(status="FAIL", error=str(error))
            results.append(result)
            print(f"{result['status']} {assay}/{method}: {len(ids)} eligible samples; {result.get('error', 'each selected sample represented exactly once')}", flush=True)
            artifact = {"time": datetime.now(timezone.utc).isoformat(), "api": args.api,
                        "scope": "Job completion, Newick syntax and exact selected leaf set; biological distance calibration and UI remain separate checks",
                        "results": results}
            (root / "species-clustering-results.json").write_text(json.dumps(artifact, indent=2) + "\n")
    if any(row["status"] != "PASS" for row in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
