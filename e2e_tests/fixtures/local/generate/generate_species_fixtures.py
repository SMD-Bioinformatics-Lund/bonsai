#!/usr/bin/env python3
"""Prepare synthetic UI cases for all configured Bonsai/JASEN assay paths.

No pipeline predictions or public biological data are used. Generated payloads,
helper snapshots and expectations are kept on the external project data drive.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1]
REPO = SOURCE.parents[2]
DEFAULT_ROOT = (Path.home() / "data/codex/bonsai/runs"
                / f"{datetime.now(timezone.utc):%Y-%m-%d}-species-ui" / "fixtures")
PROFILES = (
    ("tb", "mtuberculosis", "Mycobacterium tuberculosis", None),
    ("sa", "saureus", "Staphylococcus aureus", "saureus"),
    ("ec", "ecoli", "Escherichia coli", "ecoli_achtman_4"),
    ("kp", "kpneumoniae", "Klebsiella pneumoniae", "klebsiella"),
    ("kl", "klebsiella", "Klebsiella pneumoniae", "klebsiella"),
    ("sp", "spyogenes", "Streptococcus pyogenes", "spyogenes"),
    ("strept", "streptococcus", "Streptococcus dysgalactiae", None),
    ("staph", "staphylococcus", "Staphylococcus epidermidis", None),
)
AMR_COLUMNS = (
    "Protein id", "Contig id", "Start", "Stop", "Strand", "Element symbol",
    "Element name", "Type", "Subtype", "Class", "Subclass", "Method",
    "Target length", "Reference sequence length", "% Coverage of reference",
    "% Identity to reference", "Alignment length", "Closest reference accession",
    "Closest reference name", "HMM accession", "HMM description",
)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def write_tsv(path: Path, columns: tuple | list, rows: list[dict]) -> None:
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=columns, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    path.write_text(stream.getvalue(), encoding="utf-8")


def amrfinder(path: Path, assay: str, number: int) -> list[str]:
    """Alternate explicit negative findings, AMR genes and PVL subunits."""
    symbols: list[tuple[str, str, str, str]] = []
    if number != 2:
        if assay in {"saureus", "staphylococcus"}:
            symbols.append(("mecA" if number % 2 else "ermA", "AMR", "AMR", "BETA-LACTAM"))
            if assay == "saureus":
                symbols.append(("lukF-PV", "VIRULENCE", "TOXIN", "NA"))
                if number != 3:
                    symbols.append(("lukS-PV", "VIRULENCE", "TOXIN", "NA"))
        elif assay in {"ecoli", "kpneumoniae", "klebsiella"}:
            symbols.append(("blaCTX-M-15", "AMR", "AMR", "CEPHALOSPORIN"))
            symbols.append(("gyrA_S83L", "AMR", "POINT", "QUINOLONE"))
        else:
            symbols.append(("ermB", "AMR", "AMR", "MACROLIDE"))
    rows = []
    for index, (symbol, kind, subtype, drug) in enumerate(symbols, start=1):
        row = dict.fromkeys(AMR_COLUMNS, "NA")
        row.update({
            "Protein id": f"synthetic_protein_{index}", "Contig id": "synthetic_contig",
            "Start": index * 1000, "Stop": index * 1000 + 299, "Strand": "+",
            "Element symbol": symbol, "Element name": f"Synthetic {symbol} parser input",
            "Type": kind, "Subtype": subtype, "Class": drug, "Subclass": drug,
            "Method": "POINT" if subtype == "POINT" else "EXACTX", "Target length": 100,
            "Reference sequence length": 100, "% Coverage of reference": 100,
            "% Identity to reference": 99, "Alignment length": 100,
            "Closest reference accession": f"SYNTHETIC_{index}",
            "Closest reference name": symbol,
        })
        rows.append(row)
    write_tsv(path, AMR_COLUMNS, rows)
    return [item[0] for item in symbols]


def kleborate(path: Path, sid: str, number: int) -> None:
    """Small Kleborate report; retained as a separate ingestion scenario."""
    row = {
        "strain": sid,
        "enterobacterales__species__species": "Klebsiella pneumoniae",
        "enterobacterales__species__species_match": "strong",
        "klebsiella_pneumo_complex__virulence_score__virulence_score": 0 if number == 2 else 3,
        "klebsiella_pneumo_complex__virulence_score__spurious_virulence_hits": "-",
    }
    for method, locus, kind in (("K", "KL2", "K2"), ("O", "O1v1", "O1")):
        for key, value in {
            f"{method}_locus": locus, f"{method}_type": kind,
            f"{method}_locus_identity": 0.99, f"{method}_locus_confidence": "typeable",
            f"{method}_locus_problems": "-", f"{method}_Missing_expected_genes": "-",
        }.items():
            row[f"klebsiella_pneumo_complex__{key}"] = value
    write_tsv(path, list(row), [row])


def manifest(sid: str, assay: str, number: int, analyses: list[dict]) -> dict:
    return {
        "sample_id": sid, "sample_name": f"Synthetic {assay} sample {number:03d}",
        "lims_id": f"SYNTHETIC-LIMS-{assay.upper()}-{number:03d}", "groups": [assay],
        "metadata": [
            {"fieldname": "data classification", "value": "synthetic", "type": "string", "category": "general"},
            {"fieldname": "isolation date", "value": f"2025-01-{number:02d}", "type": "datetime", "category": "general"},
            {"fieldname": "region", "value": f"synthetic-region-{1 if number < 4 else 2}", "type": "string", "category": "general"},
        ],
        "nextflow_run_info": "analysis_meta.json", "analysis_result": analyses,
        "index_artifacts": {"sourmash_signature": f"{sid}.sig", "ska_index": f"{sid}_ska_index.skf"},
    }


def analysis(software: str, filename: str, version: str) -> dict:
    return {"software": software, "software_version": version, "uri": filename}


def generate(root: Path) -> dict:
    spec = importlib.util.spec_from_file_location("baseline_fixtures", SOURCE / "generate/generate_fixtures.py")
    baseline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline)
    baseline.FIXTURE_ROOT = root
    baseline.SAMPLE_ROOT = root / "samples"
    baseline.main()
    expectations = []
    for profile_index, (prefix, assay, species, scheme) in enumerate(PROFILES):
        sequence = baseline.deterministic_dna(f"bonsai-local-test:{assay}", baseline.GENOME_LENGTH)
        for number in range(1, baseline.SAMPLE_COUNT + 1):
            sid = f"synthetic_{prefix}_{number:03d}"
            folder = root / "samples" / sid
            folder.mkdir(parents=True, exist_ok=True)
            mutations = baseline.mutation_count(number)
            baseline.write_fasta(folder / f"{sid}.fasta", sid, baseline.mutate(sequence, mutations))
            baseline.write_analysis_meta(folder / "analysis_meta.json", sid, assay, number)
            # Taxonomy IDs are synthetic. Exact species names intentionally exercise
            # application tag/threshold dispatch while metadata labels all cases synthetic.
            baseline.write_bracken(folder / "bracken.out", species, 990000 + profile_index, number)
            baseline.write_quast(folder / "quast.tsv", sid, number)
            analyses = [analysis("bracken", "bracken.out", "2.8.0"), analysis("quast", "quast.tsv", "5.2.0")]
            expected = {"sample_id": sid, "assay": assay, "species": species,
                        "sample_name": f"Synthetic {assay} sample {number:03d}",
                        "lims_id": f"SYNTHETIC-LIMS-{assay.upper()}-{number:03d}",
                        "substitutions_from_group_reference": mutations,
                        "n_contigs": 1, "assembly_length": 100000, "n50": 100000 - number,
                        "mlst": None, "cgmlst": assay != "mtuberculosis", "deferred_analyses": []}
            if scheme:
                baseline.write_mlst(folder / "mlst.json", sid, number)
                mlst = json.loads((folder / "mlst.json").read_text())
                mlst[0]["scheme"] = scheme
                write_json(folder / "mlst.json", mlst)
                analyses.append(analysis("mlst", "mlst.json", "2.23.0"))
                expected["mlst"] = {"scheme": scheme, "sequence_type": str(100 + number)}
            if assay != "mtuberculosis":
                baseline.write_chewbbaca(folder / "chewbbaca.out", sid, number, mutations)
                analyses.append(analysis("chewbbaca", "chewbbaca.out", "3.3.10"))
                expected["amrfinder_symbols"] = amrfinder(folder / "amrfinder.tsv", assay, number)
                analyses.append(analysis("amrfinder", "amrfinder.tsv", "4.2.7"))
            else:
                baseline.write_extended_results(folder, sid, number)
                analyses += [analysis("mykrobe", "mykrobe.csv", "0.12.2"), analysis("postalignqc", "postalignqc.json", "1.0.0")]
                if number != 10:
                    analyses.append(analysis("tbprofiler", "tbprofiler.json", "6.3.0"))
                expected.update({"tbprofiler_present": number != 10, "tbprofiler_variant_count": 0 if number in {2, 10} else 3,
                                 "lineage": None if number == 10 else "lineage2.2.1", "n_reads": 1000, "n_dup_reads": 10,
                                 "mean_depth": 24.5, "median_depth": 20})
            if assay in {"saureus", "staphylococcus"}:
                write_tsv(folder / "spatyper.tsv", ["Sequence name", "Repeats", "Type"], [] if number == 2 else [
                    {"Sequence name": sid, "Repeats": "15-12-16-02", "Type": "t021"}])
                scc = {"sample": sid, "type": "IV", "subtype": "IVa", "mecA": "+",
                       "targets": "mecA,ccrA2", "regions": "IVa", "coverage": "99", "hits": "2",
                       "target_schema": "synthetic_targets", "target_schema_version": "1.2.0",
                       "region_schema": "synthetic_regions", "region_schema_version": "1.2.0",
                       "camlhmp_version": "1.1.0"}
                if number == 2:
                    scc.update(dict.fromkeys(("type", "subtype", "mecA", "targets", "regions", "coverage", "hits"), "-"))
                    write_tsv(root / "cases/sccmec-empty.tsv", list(scc), [])
                write_tsv(folder / "sccmec.tsv", list(scc), [scc])
                analyses += [analysis("spatyper", "spatyper.tsv", "0.3.3"), analysis("sccmectyper", "sccmec.tsv", "1.2.0")]
                expected.update({"spa": None if number == 2 else "t021", "sccmec": None if number == 2 else "IV"})
            if assay == "ecoli":
                source = "virulencefinder-empty.json" if number == 2 else "virulencefinder.json"
                shutil.copyfile(root / "cases" / source, folder / "virulencefinder.json")
                shutil.copyfile(root / "cases/serotypefinder.json", folder / "serotypefinder.json")
                analyses += [analysis("virulencefinder", "virulencefinder.json", "3.0.0"), analysis("serotypefinder", "serotypefinder.json", "2.0.0")]
                expected.update({"stx": None if number == 2 else "stx2",
                                 "stx_hits": [] if number == 2 else ["stx2a"],
                                 "o_type": "O157", "h_type": "H7"})
            if assay in {"spyogenes", "streptococcus"}:
                (folder / "emmtyper.tsv").write_text("" if number == 2 else f"{sid}\t1\tEMM1.0\t-\tA-C3\n")
                analyses.append(analysis("emmtyper", "emmtyper.tsv", "0.2.0"))
                expected["emm"] = None if number == 2 else "EMM1.0"
            if assay in {"kpneumoniae", "klebsiella"}:
                kleborate(folder / "kleborate.tsv", sid, number)
                hamr = {"Input_file_name": sid, "Gene_symbol": "blaCTX-M-15",
                        "Reference_database_name": "synthetic", "Reference_database_version": "1.0",
                        "Software_name": "kleborate", "Software_version": "3.2.4",
                        "Genetic_variation_type": "gene", "Reference_accession": "SYNTHETIC_BLA",
                        "Input_sequence_ID": "synthetic_contig", "Input_gene_start": 1000,
                        "Input_gene_stop": 1299, "Input_gene_length": 300, "Reference_gene_start": 1,
                        "Reference_gene_stop": 300, "Reference_gene_length": 300,
                        "Strand_orientation": "+", "Sequence_identity": 99, "Coverage": 100,
                        "Drug_class": "beta-lactam"}
                write_tsv(folder / "hamronization.tsv", list(hamr), [] if number == 2 else [hamr])
                deferred = analysis("kleborate", "kleborate.tsv", "3.2.4")
                deferred["hamronization_source"] = "hamronization.tsv"
                expected["deferred_analyses"].append(deferred)
                expected.update({"k_type": "K2", "o_type": "O1", "virulence_score": 0 if number == 2 else 3})
            write_json(folder / f"{sid}.manifest.yml", manifest(sid, assay, number, analyses))
            expectations.append(expected)

    # Existing API helpers resolve data relative to themselves; snapshots keep the
    # unchanged helpers usable with an entirely external fixture directory.
    for filename in ("seed.sh", "smoke_test.py", "scenario_test.py", "validate_fixtures.py", "validate_indexes.py", "validate_species_fixtures.py"):
        shutil.copyfile(SOURCE / filename, root / filename)
    (root / "generate").mkdir(exist_ok=True)
    for filename in ("generate_fixtures.py", "build_resources.py", "generate_species_fixtures.py"):
        shutil.copyfile(SOURCE / "generate" / filename, root / "generate" / filename)
    bootstrap = {
        "users": [
            {"username": "user_one", "email": "user_one@example.org", "password": "user123", "roles": ["user"]},
            {"username": "user_two", "email": "user_two@example.org", "password": "user123", "roles": ["user"]},
            {"username": "uploader", "email": "uploader@example.org", "password": "user123", "roles": ["uploader"]},
        ],
        "groups": [{"group_key": assay, "display_name": f"{assay} (synthetic)",
                    "description": f"Synthetic UI fixtures for {species}; no pipeline was executed"}
                   for _, assay, species, _ in PROFILES],
        "reference_genomes": [],
    }
    write_json(root / "bootstrap.yml", bootstrap)
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    result = {"created_at": datetime.now(timezone.utc).isoformat(), "bonsai_commit": commit,
              "synthetic": True, "pipeline_executed": False, "taxonomy_ids_are_synthetic": True,
              "sample_count": len(expectations), "samples_per_assay": baseline.SAMPLE_COUNT,
              "samples": expectations,
              "edge_cases": [{"software": "sccmectyper", "software_version": "1.2.0",
                              "uri": "cases/sccmec-empty.tsv", "expected": "empty result without a parser exception"}],
              "notes": ["Kleborate reports are separate ingestion checks so a rejected upload does not interrupt baseline seeding.",
                        "Generic streptococcus/staphylococcus cases intentionally have no MLST scheme.",
                        "No registered genome resources are assumed until build_resources.py and scenario setup pass."]}
    write_json(root / "expectations.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    if root == SOURCE or REPO == root or REPO in root.parents:
        parser.error("Generated payloads must be stored outside the source checkout")
    root.mkdir(parents=True, exist_ok=True)
    expected = generate(root)
    checksums = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "checksums.sha256" and "__pycache__" not in path.parts:
            checksums.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root)}\n")
    (root / "checksums.sha256").write_text("".join(checksums), encoding="utf-8")
    print(f"Prepared {expected['sample_count']} synthetic samples across {len(PROFILES)} assay paths at {root}")
    print("Signatures, SKA indexes, indexed resources and live UI validation remain separate steps.")


if __name__ == "__main__":
    main()
