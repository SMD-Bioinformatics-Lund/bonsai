#!/usr/bin/env python3
"""
Generate deterministic, entirely synthetic Bonsai local-test fixtures. 
Intended as a more elaborate local test dataset with support for multi-sample groups,
minimal clustering and such.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path


FIXTURE_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_ROOT = FIXTURE_ROOT / "samples"
GENOME_LENGTH = 100_000
# Adjust this value to change the number of generated samples per species.
SAMPLE_COUNT = 10
MUTATION_PROFILE = (0, 3, 8, 30, 100)
DNA = "ACGT"
GENERATED_SAMPLE_PATTERN = re.compile(r"synthetic_(?:tb|sa)_\d+")


def deterministic_dna(label: str, length: int) -> str:
    """Return stable pseudo-random DNA without relying on Python's RNG."""
    bases: list[str] = []
    counter = 0
    while len(bases) < length:
        digest = hashlib.sha256(f"{label}:{counter}".encode()).digest()
        bases.extend(DNA[byte & 3] for byte in digest)
        counter += 1
    return "".join(bases[:length])


def mutate(sequence: str, count: int) -> str:
    """Apply a nested set of well-spaced substitutions."""
    result = list(sequence)
    for index in range(count):
        position = 1_000 + index * 811
        result[position] = DNA[(DNA.index(result[position]) + 1) % len(DNA)]
    return "".join(result)


def mutation_count(sample_number: int) -> int:
    """Interpolate a mutation count across the fixed distance profile."""
    if not 1 <= sample_number <= SAMPLE_COUNT:
        raise ValueError(f"sample_number must be between 1 and {SAMPLE_COUNT}")
    if SAMPLE_COUNT == 1:
        return MUTATION_PROFILE[0]

    profile_position = (
        (sample_number - 1) * (len(MUTATION_PROFILE) - 1) / (SAMPLE_COUNT - 1)
    )
    lower_index = int(profile_position)
    upper_index = min(lower_index + 1, len(MUTATION_PROFILE) - 1)
    fraction = profile_position - lower_index
    return round(
        MUTATION_PROFILE[lower_index]
        + fraction
        * (MUTATION_PROFILE[upper_index] - MUTATION_PROFILE[lower_index])
    )


def remove_stale_sample_dirs() -> None:
    """Remove generated sample directories outside the configured range."""
    expected = {
        f"synthetic_{prefix}_{sample_number:03d}"
        for prefix in ("tb", "sa")
        for sample_number in range(1, SAMPLE_COUNT + 1)
    }
    if not SAMPLE_ROOT.exists():
        return

    for sample_dir in SAMPLE_ROOT.iterdir():
        if (
            sample_dir.is_dir()
            and GENERATED_SAMPLE_PATTERN.fullmatch(sample_dir.name)
            and sample_dir.name not in expected
        ):
            shutil.rmtree(sample_dir)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_fasta(path: Path, sample_id: str, sequence: str) -> None:
    lines = [f">{sample_id} synthetic=true"]
    lines.extend(sequence[pos : pos + 80] for pos in range(0, len(sequence), 80))
    write_text(path, "\n".join(lines) + "\n")


def write_analysis_meta(path: Path, sample_id: str, assay: str, sample_number: int) -> None:
    metadata = {
        "workflow_name": f"synthetic_fixture_{sample_number:03d}",
        "sample_name": sample_id,
        "lims_id": f"SYNTHETIC-LIMS-{sample_number:03d}",
        "assay": assay,
        "release_life_cycle": "development",
        "sequencing_run": "synthetic-run",
        "sequencing_platform": "illumina",
        "sequencing_type": "PE",
        "date": f"2025-01-{sample_number:02d}T12:00:00+00:00",
        "pipeline": "synthetic.nf",
        "version": "1.0.0",
        "commit": "synthetic",
        "configuration_files": ["synthetic.config"],
        "analysis_profile": [assay, "synthetic"],
        "command": "synthetic fixture generation; no pipeline was executed",
    }
    write_text(path, json.dumps(metadata, indent=2) + "\n")


def write_bracken(path: Path, organism: str, taxonomy_id: int, sample_number: int) -> None:
    assigned = 900_000 - sample_number * 1_000
    content = (
        "name\ttaxonomy_id\ttaxonomy_lvl\tkraken_assigned_reads\tadded_reads\t"
        "new_est_reads\tfraction_total_reads\n"
        f"{organism}\t{taxonomy_id}\tS\t{assigned}\t90000\t{assigned + 90000}\t0.99000\n"
        "Synthetic background organism\t999999\tS\t1000\t0\t1000\t0.00100\n"
    )
    write_text(path, content)


def write_quast(path: Path, sample_id: str, sample_number: int) -> None:
    total_length = GENOME_LENGTH
    n50 = GENOME_LENGTH - sample_number
    content = (
        "Assembly\t# contigs\tLargest contig\tTotal length\tReference length\t"
        "GC (%)\tReference GC (%)\tN50\tNG50\tDuplication ratio\n"
        f"{sample_id}\t1\t{total_length}\t{total_length}\t{total_length}\t"
        f"50.00\t50.00\t{n50}\t{n50}\t1.000\n"
    )
    write_text(path, content)


def write_mlst(path: Path, sample_id: str, sample_number: int) -> None:
    genes = ("arcC", "aroE", "glpF", "gmk", "pta", "tpi", "yqiL")
    alleles = {
        gene: str(1 + (sample_number if idx < sample_number - 1 else 0))
        for idx, gene in enumerate(genes)
    }
    result = [{
        "alleles": alleles,
        "id": f"{sample_id}.fasta",
        "scheme": "saureus",
        "filename": f"{sample_id}.fasta",
        "sequence_type": str(100 + sample_number),
    }]
    write_text(path, json.dumps(result, indent=2) + "\n")


def write_chewbbaca(
    path: Path, sample_id: str, sample_number: int, mutations: int
) -> None:
    loci = [f"SYNLOC{index:04d}" for index in range(1, 31)]
    changed_loci = mutations // 3
    alleles = [
        str(1 + sample_number) if index < changed_loci else "1"
        for index, _ in enumerate(loci)
    ]
    write_text(
        path,
        "FILE\t" + "\t".join(loci) + "\n"
        + sample_id + "\t" + "\t".join(alleles) + "\n",
    )


def write_manifest(
    path: Path,
    sample_id: str,
    group_id: str,
    assay: str,
    sample_number: int,
    include_allele_profiles: bool,
) -> None:
    analysis = """  - software: bracken
    software_version: 1.0.0
    database: synthetic
    uri: bracken.out
  - software: quast
    software_version: 1.0.0
    uri: quast.tsv
"""
    if include_allele_profiles:
        analysis += """  - software: mlst
    software_version: 1.0.0
    uri: mlst.json
  - software: chewbbaca
    software_version: 1.0.0
    uri: chewbbaca.out
"""

    manifest = f"""# Generated test data only. It does not describe a biological isolate.
sample_id: {sample_id}
sample_name: Synthetic {assay} sample {sample_number:03d}
lims_id: SYNTHETIC-LIMS-{assay.upper()}-{sample_number:03d}
groups:
  - {group_id}
metadata:
  - fieldname: data classification
    value: synthetic
    type: string
    category: general
  - fieldname: isolation date
    value: 2025-01-{sample_number:02d}
    type: datetime
    category: general
  - fieldname: region
    value: synthetic-region-{1 if sample_number < 4 else 2}
    type: string
    category: general

nextflow_run_info: analysis_meta.json

analysis_result:
{analysis}
index_artifacts:
  sourmash_signature: {sample_id}.sig
  ska_index: {sample_id}_ska_index.skf
"""
    write_text(path, manifest)


def generate_species(prefix: str, group_id: str, assay: str, organism: str, taxonomy_id: int) -> None:
    base_sequence = deterministic_dna(f"bonsai-local-test:{assay}", GENOME_LENGTH)
    for sample_number in range(1, SAMPLE_COUNT + 1):
        sample_id = f"synthetic_{prefix}_{sample_number:03d}"
        sample_dir = SAMPLE_ROOT / sample_id
        sample_dir.mkdir(parents=True, exist_ok=True)
        mutations = mutation_count(sample_number)
        sequence = mutate(base_sequence, mutations)
        write_fasta(sample_dir / f"{sample_id}.fasta", sample_id, sequence)
        write_analysis_meta(sample_dir / "analysis_meta.json", sample_id, assay, sample_number)
        write_bracken(sample_dir / "bracken.out", organism, taxonomy_id, sample_number)
        write_quast(sample_dir / "quast.tsv", sample_id, sample_number)
        include_allele_profiles = group_id == "saureus"
        if include_allele_profiles:
            write_mlst(sample_dir / "mlst.json", sample_id, sample_number)
            write_chewbbaca(
                sample_dir / "chewbbaca.out", sample_id, sample_number, mutations
            )
        write_manifest(
            sample_dir / f"{sample_id}.manifest.yml",
            sample_id,
            group_id,
            assay,
            sample_number,
            include_allele_profiles,
        )


def main() -> None:
    if SAMPLE_COUNT < 1:
        raise ValueError("SAMPLE_COUNT must be at least 1")
    remove_stale_sample_dirs()
    generate_species(
        prefix="tb",
        group_id="mtuberculosis",
        assay="mtuberculosis",
        organism="Synthetic Mycobacterium tuberculosis surrogate",
        taxonomy_id=1773,
    )
    generate_species(
        prefix="sa",
        group_id="saureus",
        assay="saureus",
        organism="Synthetic Staphylococcus aureus surrogate",
        taxonomy_id=1280,
    )
    print(f"Generated {SAMPLE_COUNT * 2} samples under {SAMPLE_ROOT}")


if __name__ == "__main__":
    main()
