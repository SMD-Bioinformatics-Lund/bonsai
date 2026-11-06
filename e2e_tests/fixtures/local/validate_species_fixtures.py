#!/usr/bin/env python3
"""Check synthetic species fixtures against the actual SDK parser contracts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from bonsai_libs.parse import run_parser


def parse(folder: Path, item: dict) -> dict:
    kwargs = {}
    if "hamronization_source" in item:
        kwargs["hamronization_source"] = folder / item["hamronization_source"]
    bundle = run_parser(software=item["software"], version=item["software_version"],
                        data=folder / item["uri"], **kwargs)
    errors = {str(kind): envelope.reason for kind, envelope in bundle.results.items()
              if str(envelope.status) == "error"}
    assert not errors, (folder.name, item["software"], errors)
    return bundle.results


def check(root: Path) -> tuple[int, int]:
    expectations = json.loads((root / "expectations.json").read_text())
    for line in (root / "checksums.sha256").read_text().splitlines():
        expected_hash, relative = line.split("  ", 1)
        assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected_hash, relative
    checked = 0
    for expected in expectations["samples"]:
        folder = root / "samples" / expected["sample_id"]
        manifest = json.loads((folder / f"{folder.name}.manifest.yml").read_text())
        parsed = {}
        for item in manifest["analysis_result"] + expected["deferred_analyses"]:
            parsed[item["software"]] = parse(folder, item)
            checked += 1
        assert parsed["bracken"]["species_prediction"].value[0].scientific_name == expected["species"]
        assert parsed["quast"]["qc"].value.total_length == expected["assembly_length"]
        if expected["mlst"]:
            mlst = parsed["mlst"]["mlst"].value
            assert mlst.scheme == expected["mlst"]["scheme"], (folder.name, mlst)
            assert str(mlst.sequence_type) == expected["mlst"]["sequence_type"]
        if expected["cgmlst"]:
            assert str(parsed["chewbbaca"]["cgmlst"].status) == "parsed"
        if "amrfinder_symbols" in expected:
            amr = parsed["amrfinder"]["amr"].value
            vir = parsed["amrfinder"]["virulence"].value
            symbols = {gene.gene_symbol for row in (amr, vir) if row for gene in row.genes}
            expected_genes = {symbol for symbol in expected["amrfinder_symbols"] if "_S83L" not in symbol}
            assert symbols == expected_genes, (folder.name, symbols, expected_genes)
            assert len(amr.variants if amr else []) == int("gyrA_S83L" in expected["amrfinder_symbols"])
        if expected["assay"] == "mtuberculosis":
            qc = parsed["postalignqc"]["qc"].value
            assert qc.n_reads == expected["n_reads"] and qc.n_dup_reads == expected["n_dup_reads"]
            assert qc.mean_cov == expected["mean_depth"] and qc.median_cov == expected["median_depth"]
            assert ("tbprofiler" in parsed) == expected["tbprofiler_present"]
            if "tbprofiler" in parsed:
                tb = parsed["tbprofiler"]
                assert tb["lineage"].value[0].lineage == expected["lineage"]
                assert len(tb["amr"].value.variants if tb["amr"].value else []) == expected["tbprofiler_variant_count"]
        if expected["assay"] == "ecoli":
            stx = parsed["virulencefinder"]["stx"].value
            assert (stx.gene_symbol if stx else None) == expected["stx"]
            assert ([hit.gene_symbol for hit in stx.hits] if stx else []) == expected["stx_hits"]
            assert parsed["serotypefinder"]["o_type"].value.sequence_name == expected["o_type"]
            assert parsed["serotypefinder"]["h_type"].value.sequence_name == expected["h_type"]
        if "emm" in expected:
            emm = parsed["emmtyper"]["emm"].value
            assert (emm.emmtype if emm else None) == expected["emm"]
        if "spa" in expected:
            spa = parsed["spatyper"]["spatype"].value
            assert (spa.type if spa else None) == expected["spa"]
            scc = parsed["sccmectyper"]["sccmec"].value
            assert (scc[0].type if scc else None) == expected["sccmec"]
        if "k_type" in expected:
            kleb = parsed["kleborate"]
            assert kleb["k_type"].value.type == expected["k_type"]
            assert kleb["o_type"].value.type == expected["o_type"]
            assert kleb["virulence"].value.score == expected["virulence_score"]
    return len(expectations["samples"]), checked


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--edge-cases", action="store_true")
    args = parser.parse_args()
    count, reports = check(args.root.expanduser().resolve())
    print(f"PASS {count} samples, {reports} report parses, expected species/typing/AMR/QC values and payload checksums")
    if args.edge_cases:
        root = args.root.expanduser().resolve()
        for item in json.loads((root / "expectations.json").read_text())["edge_cases"]:
            parse(root, item)
        print("PASS additional empty-report cases")


if __name__ == "__main__":
    main()
