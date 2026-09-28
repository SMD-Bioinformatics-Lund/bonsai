#!/usr/bin/env python3
"""Set up UI examples and check synthetic workflow cases through the public API."""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from uuid import uuid4

from generate.generate_fixtures import REFERENCE_NAME, SAMPLE_COUNT

ROOT = Path(__file__).resolve().parent


class Api:
    def __init__(self, url, username, password):
        self.url = url.rstrip("/")
        self.token = None
        self.token = self.request("/token", body=urlencode({"username": username, "password": password}).encode(),
                                  content_type="application/x-www-form-urlencoded")["access_token"]

    def request(self, path, *, data=None, body=None, content_type="application/json", method=None,
                expected=200, raw=False):
        if data is not None:
            body = json.dumps(data).encode()
        headers = {"Content-Type": content_type}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = Request(self.url + path, data=body, headers=headers,
                          method=method or ("POST" if body is not None else "GET"))
        try:
            response = urlopen(request, timeout=30)
        except HTTPError as error:
            response = error
        with response:
            payload = response.read()
            statuses = expected if isinstance(expected, tuple) else (expected,)
            assert response.status in statuses, (request.method, path, response.status, payload.decode(errors="replace"))
        return payload if raw else (json.loads(payload) if payload else None)

    def upload(self, sid, software, file, version, *, expected=201, **extras):
        boundary = "bonsai-fixture-" + uuid4().hex
        fields = {"sample_id": sid, "software": software, "software_version": version,
                  **{k: v for k, v in extras.items() if not isinstance(v, Path)}}
        parts = []
        for name, value in fields.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
        for name, path in {"file": file, **{k: v for k, v in extras.items() if isinstance(v, Path)}}.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{path.name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()
                         + path.read_bytes() + b"\r\n")
        body = b"".join(parts) + f"--{boundary}--\r\n".encode()
        return self.request("/analysis/", body=body, content_type=f"multipart/form-data; boundary={boundary}", expected=expected)

    def sample(self, sid):
        return self.request(f"/samples/{sid}")


def entry(sample, software, analysis_type):
    return next(row for field in ("qc_result", "typing_result", "species_prediction", "element_type_result")
                for row in sample.get(field, [])
                if row["software"] == software and row["analysis_type"] == analysis_type)


def upload_properties(schema):
    upload = schema["paths"]["/analysis/"]["post"]["requestBody"]["content"]["multipart/form-data"]["schema"]
    return schema["components"]["schemas"][upload["$ref"].split("/")[-1]]["properties"]


def curation(api, row, annotation_type, decision, result_key=None, phenotypes=None, expected=201):
    payload = {"annotation_type": annotation_type, "decision": decision,
               "comment": "Synthetic local fixture"}
    if result_key is not None:
        payload["result_key"] = str(result_key)
        payload["phenotypes"] = phenotypes or []
    if decision == "reject":
        payload["rejection_reason"] = "LOW"
    return api.request(f'/analysis/{row["analysis_id"]}/curations',
                       data={"analysis_type": row["analysis_type"], "curation": payload}, expected=expected)


def setup(api, samples, schema):
    """Add small reports and persistent curation examples without replacing samples."""
    for sample in samples:
        external = sample["external_sample_id"]
        if not external.startswith("synthetic_tb_"):
            continue
        number = int(external.rsplit("_", 1)[1])
        folder = ROOT / "samples" / external
        sources = [("mykrobe", "mykrobe.csv", "0.12.2"), ("postalignqc", "postalignqc.json", "1.0.0")]
        if number != 10:
            sources.append(("tbprofiler", "tbprofiler.json", "6.3.0"))
        present = {row["software"] for field in ("qc_result", "typing_result", "species_prediction", "element_type_result")
                   for row in sample.get(field, [])}
        for software, filename, version in sources:
            if software not in present:
                api.upload(sample["sample_id"], software, folder / filename, version)
    first = next(s for s in samples if s["external_sample_id"] == "synthetic_tb_001")
    sid = first["sample_id"]
    sample = api.sample(sid)
    for software, key, decision, drug, meta in (
        ("mykrobe", 1, "accept", "rifampicin", {}),
        ("tbprofiler", 1, "accept", "rifampicin", {}),
        ("tbprofiler", 2, "accept", "isoniazid", {"resistance_level": "high"}),
        ("tbprofiler", 3, "reject", "ethambutol", {}),
    ):
        row = entry(sample, software, "amr")
        if not any(c.get("result_key") == str(key) for c in row.get("curations", [])):
            curation(api, row, "variant", decision, key, [{"name": drug, "meta": meta}])
    print("PASS setup: TB reports and accepted/rejected curation examples")
    if "sequence_accessions" not in schema["components"]["schemas"]["ReferenceGenomeCreate"]["properties"]:
        print("SKIP resource setup: API predates PR #504")
        return
    if not (ROOT / "resources/alignment.bam.bai").exists():
        print("SKIP resource setup: regenerate artifacts with --resources to build BAM/indexes")
        return
    if not sample["pipeline"]["pipeline_info"].get("databases"):
        pipeline = json.loads(json.dumps(sample["pipeline"]))
        pipeline["pipeline_run_id"] = "synthetic_fixture_extended_tb_001"
        pipeline["pipeline_info"]["databases"] = [
            {"software": "tbprofiler", "name": "tbdb", "version": "synthetic-v1"},
            {"software": "synthetic", "name": "synthetic_unknown_db", "version": "1.0.0"},
        ]
        api.request(f"/samples/{sid}/pipeline-runs", data=pipeline)
        sample = api.sample(sid)
    refs = api.request("/reference-genomes")
    reference = next((ref for ref in refs if ref["accession"] == "SYNTHETIC_TB_ASSEMBLY"), None)
    if reference is None:
        reference = api.request("/reference-genomes", data={
            "name": "Synthetic TB reference", "accession": "SYNTHETIC_TB_ASSEMBLY",
            "organism": "Synthetic TB surrogate", "sequence_accessions": [REFERENCE_NAME],
            "fasta_resource": "reference.fasta", "fasta_index_resource": "reference.fasta.fai",
            "reference_tracks": [{"format": "bed", "type": "annotation", "name": "Synthetic locus", "path": "annotation.bed"}],
        })
    if sample.get("reference_genome_id") != reference["id"]:
        api.request(f"/samples/{sid}/reference-genome", method="PUT", data={"reference_genome_id": reference["id"]})
    if not api.request(f"/samples/{sid}/resources"):
        api.request(f"/samples/{sid}/resources", expected=201, data={
            "reference_genome_id": reference["id"], "pipeline_run_id": sample["pipeline"]["pipeline_run_id"],
            "visibility": "public", "resource_data": [{"format": "bam", "type": "alignment",
                "name": "Synthetic reads", "path": "alignment.bam", "index_path": "alignment.bam.bai"}],
        })
    print("PASS setup: shared reference, annotation and indexed alignment")


def check_curations_and_export(api, samples):
    tb = {s["external_sample_id"]: s["sample_id"] for s in samples}
    sample = api.sample(tb["synthetic_tb_001"])
    assert len(entry(sample, "tbprofiler", "amr")["curations"]) == 3
    content = api.request(f'/export/{sample["sample_id"]}/lims', raw=True).decode()
    rows = {row["parameter_name"]: row for row in csv.DictReader(io.StringIO(content), delimiter="\t")}
    assert rows["MTBC_LINEAGE"]["parameter_value"] == "2.2.1"
    rif = rows["RIF_NGS"]
    assert "450" in rif["parameter_value"] + rif["comment"] and "451" not in content, content
    assert "315" in rows["INH_NGSH"]["parameter_value"] + rows["INH_NGSH"]["comment"]
    assert rows["INH_NGSL"]["parameter_value"] == "Mutation ej pavisad"
    assert rows["ETB_NGS"]["parameter_value"] == "Mutation ej pavisad"
    if "synthetic_tb_010" in tb:
        api.request(f'/export/{tb["synthetic_tb_010"]}/lims', expected=422)
    # Use an otherwise uncurated sample, then remove only records created by this run.
    if "synthetic_tb_003" in tb:
        sid = tb["synthetic_tb_003"]
        row = entry(api.sample(sid), "tbprofiler", "amr")
        assert not row.get("curations"), "Sample 3 must start uncurated"
        created = curation(api, row, "variant", "accept", 1, [{"name": "rifampicin"}])["curation_id"]
        try:
            curation(api, row, "variant", "accept", 1, expected=409)
        finally:
            api.request(f"/analysis/curations/{created}", method="DELETE", expected=204)
        assert entry(api.sample(sid), "tbprofiler", "amr")["curations"] == []
        qc = entry(api.sample(sid), "postalignqc", "qc")
        assert not qc.get("curations"), "Sample 3 QC must start uncurated"
        created = curation(api, qc, "qc", "pass")["curation_id"]
        try:
            curation(api, qc, "qc", "pass", expected=409)
        finally:
            api.request(f"/analysis/curations/{created}", method="DELETE", expected=204)
        assert entry(api.sample(sid), "postalignqc", "qc")["curations"] == []
    print("PASS LIMS and curation: source selection, resistance levels, rejection, duplicate conflict and final deletion")


def check_ingestion(api, schema):
    created = []
    suffix = uuid4().hex[:12]
    def create(lims, run, expected=201):
        result = api.request("/samples/", expected=expected, data={
            "sample_id": f"fixture-case-{uuid4().hex}", "sample_name": "Synthetic scenario " + suffix,
            "lims_id": lims, "sequencing": {"sequencing_run_id": run, "platform": "illumina"},
        })
        if expected == 201:
            result["sample_id"] = result["internal_sample_id"]
            created.append(result["sample_id"])
        return result
    try:
        sid = create("fixture-" + suffix, "run-1")["sample_id"]
        create("fixture-" + suffix, "run-1", expected=409)
        create("fixture-" + suffix, "run-2")
        for blank in (None, "", "   "):
            for _ in range(2):
                absent = create(blank, blank)
                assert api.sample(absent["sample_id"])["lims_id"] is None
        api.upload(sid, "virulencefinder", ROOT / "cases/virulencefinder.json", "3.0.0")
        sample = api.sample(sid)
        # The placement assertion also catches the regression fixed in PR #504.
        vir = next((r for r in sample["element_type_result"] if r["analysis_type"] == "virulence"), None)
        if vir is None and "subcommand" not in upload_properties(schema):
            print("SKIP virulence placement: API predates PR #504")
        else:
            assert vir and vir["result"]["genes"][0]["gene_symbol"] == "synthetic_vir"
        gene_row = entry(sample, "virulencefinder", "virulence")
        gene_curation = curation(api, gene_row, "gene", "accept", "synthetic_vir")["curation_id"]
        try:
            curation(api, gene_row, "gene", "accept", "synthetic_vir", expected=409)
        finally:
            api.request(f"/analysis/curations/{gene_curation}", method="DELETE", expected=204)
        assert entry(api.sample(sid), "virulencefinder", "virulence")["curations"] == []
        assert entry(sample, "virulencefinder", "stx")["result"]["gene_symbol"] == "stx2a"
        api.upload(sid, "serotypefinder", ROOT / "cases/serotypefinder.json", "2.0.0")
        assert entry(api.sample(sid), "serotypefinder", "o_type")["result"]["sequence_name"] == "O157"
        empty_sid = created[-1]
        api.upload(empty_sid, "virulencefinder", ROOT / "cases/virulencefinder-empty.json", "3.0.0")
        empty = api.sample(empty_sid)
        assert entry(empty, "virulencefinder", "virulence")["result"]["genes"] == []
        assert entry(empty, "virulencefinder", "stx")["status"] in ("absent", "empty")
        failed = {"status": "failed", "action": "resequence", "comment": "Synthetic failed-QC case"}
        for _ in range(2):
            assert api.request(f"/samples/{empty_sid}/qc_status", method="PUT", data=failed) == failed
        assert api.sample(empty_sid)["qc_status"] == failed
        restored = {"status": "unprocessed", "action": None, "comment": ""}
        assert api.request(f"/samples/{empty_sid}/qc_status", method="PUT", data=restored) == restored
        print("PASS gene curation uniqueness/deletion and failed-QC classification/action/comment")
        for method, strategy in (("mlst", "MSTree"), ("cgmlst", "MSTree"), ("ska", "single")):
            api.request(f"/cluster/{method}", data={"sampleIds": [sid, empty_sid], "method": strategy}, expected=404)
        print("PASS missing typing profiles and SKA index rejected before queuing")
        properties = upload_properties(schema)
        if "coverage_file" in properties:
            folder = ROOT / "samples/synthetic_tb_001"
            api.upload(sid, "samtools", folder / "samtools.stats", "1.21", subcommand="stats",
                       coverage_file=folder / "samtools.coverage", bedcov_file=folder / "samtools.bedcov")
            qc = entry(api.sample(sid), "postalignqc", "qc")["result"]
            assert qc["mean_cov"] == 24.5 and qc["pct_above_x"]["30"] == 40
            api.upload(sid, "samtools", folder / "samtools.coverage", "1.21", subcommand="coverage")
            assert entry(api.sample(sid), "samtools", "qc")["status"] == "parsed"
            api.upload(sid, "samtools", folder / "samtools.stats", "1.21", subcommand="stats", expected=409)
            print("PASS auxiliary QC upload and subcommand identity")
        else:
            print("SKIP auxiliary QC upload: API predates PR #504; reports validated offline")
        print("PASS ingestion: duplicate/missing IDs, virulence/STX and serotype")
        api.upload(sid, "tbprofiler", ROOT / "cases/malformed.json", "6.3.0", expected=422)
    finally:
        for sid in reversed(created):
            api.request(f"/samples/{sid}", method="DELETE")
    print("PASS malformed report rejected; temporary samples removed")


def check_qc_and_resources(api, samples, schema):
    first = next(s for s in samples if s["external_sample_id"] == "synthetic_tb_001")
    sid = first["sample_id"]
    summary = api.request("/samples/summary", data={"sid": [sid], "fields": [
        "sample_id", "postalignqc_median_cov", "postalignqc_n_reads",
        "postalignqc_coverage_10", "postalignqc_coverage_30", "quast_n_contigs"], "limit": 0})
    row = summary["data"][0]
    assert row["postalignqc_median_cov"] == 20 and row["postalignqc_n_reads"] == 1000, row
    assert row["postalignqc_coverage_10"] == 80 and row["postalignqc_coverage_30"] == 40, row
    assert row["quast_n_contigs"] == 1
    # Same-status updates are safe to repeat and must return the classification.
    sample = api.sample(sid)
    qc = sample["qc_status"]
    assert api.request(f"/samples/{sid}/qc_status", data=qc, method="PUT") == qc
    print("PASS QC: populated summary coverage columns and repeated classification update")
    if "sequence_accessions" not in schema["components"]["schemas"]["ReferenceGenomeCreate"]["properties"]:
        print("SKIP resource checks: API predates PR #504")
        return
    refs = api.request("/reference-genomes")
    reference = next(ref for ref in refs if ref["accession"] == "SYNTHETIC_TB_ASSEMBLY")
    # Lookup is exposed by reference assignment, rather than a reference GET route.
    try:
        for identifier in (reference["accession"], REFERENCE_NAME):
            found = api.request(f"/samples/{sid}/reference-genome", method="PUT",
                                data={"reference_genome_id": identifier}, expected=(200, 304))
            if found is not None:
                assert found["id"] == reference["id"]
    finally:
        api.request(f"/samples/{sid}/reference-genome", method="PUT",
                    data={"reference_genome_id": reference["id"]}, expected=(200, 304))
    config = api.request(f"/samples/{sid}/igv-config")
    assert config["reference"]["fastaURL"] == reference["fasta_url"]
    alignment = next(track for track in config["tracks"] if track["format"] == "bam")
    for url, filename in ((config["reference"]["fastaURL"], "reference.fasta"),
                          (config["reference"]["indexURL"], "reference.fasta.fai"),
                          (alignment["url"], "alignment.bam"), (alignment["indexURL"], "alignment.bam.bai")):
        parsed = urlsplit(url)
        path = parsed.path + ("?" + parsed.query if parsed.query else "")
        assert api.request(path, raw=True) == (ROOT / "resources" / filename).read_bytes()
    print("PASS resources: ID/accession lookup, IGV configuration and served FASTA/BAM/index bytes")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default=os.environ.get("BONSAI_API", "http://localhost:18001"))
    parser.add_argument("--username", default=os.environ.get("BONSAI_USERNAME", "admin"))
    parser.add_argument("--password", default=os.environ.get("BONSAI_PASSWORD", "admin123"))
    parser.add_argument("--setup", action="store_true", help="Add reports, curations and resources for subsequent tests/UI inspection")
    parser.add_argument("--setup-only", action="store_true", help="Prepare persistent UI examples without running regression checks")
    parser.add_argument("--require-current-api", action="store_true", help="Fail instead of skipping checks that require PR #504")
    args = parser.parse_args()
    api = Api(args.api, args.username, args.password)
    schema = api.request("/openapi.json")
    if args.require_current_api:
        assert "coverage_file" in upload_properties(schema), "This run requires an API including PR #504"
    samples = api.request("/samples?limit=0")["data"]
    samples = [s for s in samples if s.get("external_sample_id", "").startswith(("synthetic_tb_", "synthetic_sa_"))]
    assert len(samples) == SAMPLE_COUNT * 2, "Seed the baseline synthetic dataset first"
    if args.setup or args.setup_only:
        setup(api, samples, schema)
    if args.setup_only:
        return
    failures = []
    for check in (check_curations_and_export, check_qc_and_resources, check_ingestion):
        try:
            if check is check_curations_and_export:
                check(api, samples)
            elif check is check_qc_and_resources:
                check(api, samples, schema)
            else:
                check(api, schema)
        except Exception as error:
            failures.append(check.__name__)
            print(f"FAIL {check.__name__}: {error}", flush=True)
    if failures:
        raise SystemExit(f"Scenario checks failed: {', '.join(failures)}")


if __name__ == "__main__":
    main()
