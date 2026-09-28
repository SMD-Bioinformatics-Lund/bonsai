#!/usr/bin/env python3
"""
Generate deterministic, entirely synthetic Bonsai local-test fixtures. 
Intended as a more elaborate local test dataset with support for multi-sample groups,
minimal clustering and such.
"""

from __future__ import annotations

import hashlib
import csv
import io
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
REFERENCE_NAME = "SYNTHETIC_TB_CONTIG"


def write_json(path: Path, value: object) -> None:
    write_text(path, json.dumps(value, indent=2) + "\n")


def write_extended_results(sample_dir: Path, sample_id: str, number: int) -> None:
    """Small reports crafted for parser/workflow tests, not biological predictions."""
    variants = []
    for pos, gene, drug, change in (
        (2001, "rpoB", "rifampicin", "p.Ser450Leu"),
        (4001, "katG", "isoniazid", "p.Ser315Thr"),
        (6001, "embB", "ethambutol", "p.Met306Val"),
    ):
        variants.append({
            "gene_name": gene, "feature_id": REFERENCE_NAME, "pos": pos,
            "ref": "C", "alt": "T", "type": "missense_variant",
            "nucleotide_change": f"c.{pos}C>T", "protein_change": change,
            "depth": 40, "freq": 0.95, "gene_associated_drugs": [drug],
            "annotation": [{"drug": drug, "confidence": "synthetic",
                            "comment": "Synthetic test annotation"}],
        })
    # Sample 2 has an explicit no-findings report; sample 10 omits it in its manifest.
    write_json(sample_dir / "tbprofiler.json", {
        "dr_variants": variants[:2] if number != 2 else [],
        "other_variants": [], "qc_fail_variants": variants[2:] if number != 2 else [],
        "lineage": [{"lineage": "lineage2.2.1", "family": "synthetic",
                     "rd": "synthetic", "fraction": 1.0, "support": []}],
        "pipeline": {"software": [{"process": "variant_calling", "software": "synthetic"}]},
    })
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["sample", "mykrobe_version", "drug", "susceptibility", "genotype_model",
                     "variants", "species", "species_per_covg", "phylo_group",
                     "phylo_group_per_covg", "lineage"])
    writer.writerow([sample_id, "0.12.2", "Rifampicin", "R" if number != 2 else "S",
                     "kmer_count", "rpoB_S451L-TCG2004TTG:2:38:100" if number != 2 else "",
                     "Mycobacterium_tuberculosis", "99", "Mycobacterium_tuberculosis_complex",
                     "99", "lineage2.2.1"])
    write_text(sample_dir / "mykrobe.csv", stream.getvalue())
    write_json(sample_dir / "postalignqc.json", {
        "n_reads": 1000, "n_read_pairs": 500, "n_mapped_reads": 900, "n_dup_reads": 10,
        "dup_pct": 1.0, "ins_size": 300, "ins_size_dev": 20, "mean_cov": 24.5,
        "median_cov": 20, "quartile1": 20, "quartile3": 40,
        "coverage_uniformity": 1.0, "restricted_mean_cov": 35,
        "pct_above_x": {"1": 90, "10": 80, "30": 40, "100": 0, "250": 0,
                        "500": 0, "1000": 0},
    })
    write_text(sample_dir / "samtools.stats", """SN\traw total sequences:\t1000
SN\treads mapped:\t900
SN\treads paired:\t500
SN\treads duplicated:\t10
SN\tinsert size average:\t300
SN\tinsert size standard deviation:\t20
COV\t[5-5]\t5\t10000
COV\t[20-20]\t20\t40000
COV\t[40-40]\t40\t40000
""")
    write_text(sample_dir / "samtools.coverage", (
        "#rname\tstartpos\tendpos\tnumreads\tcovbases\tcoverage\tmeandepth\tmeanbaseq\tmeanmapq\n"
        f"{REFERENCE_NAME}\t1\t100000\t900\t90000\t90\t24.5\t35\t60\n"
    ))
    write_text(sample_dir / "samtools.bedcov", f"{REFERENCE_NAME}\t1000\t2000\t35000\n")


def write_typing_cases() -> None:
    """Unseeded E. coli reports for scenario uploads, without another genome/index."""
    cases = FIXTURE_ROOT / "cases"
    hit = {"name": "synthetic_vir", "ref_acc": "SYNTHETIC_VIR", "ref_start_pos": 1,
           "ref_end_pos": 100, "ref_seq_length": 100, "alignment_length": 100,
           "identity": 99.0, "coverage": 100.0}
    stx = {**hit, "name": "stx2a"}
    write_json(cases / "virulencefinder.json", {
        "databases": {}, "software_executions": {},
        "seq_regions": {"vir": hit, "stx": stx},
        "phenotypes": {
            "vir": {"function": "Synthetic virulence factor", "ref_database": ["virulence"],
                    "seq_regions": ["vir"]},
            "stx2a": {"function": "Synthetic toxin", "ref_database": ["stx"],
                      "seq_regions": ["stx"]},
        },
    })
    write_json(cases / "virulencefinder-empty.json", {
        "databases": {}, "software_executions": {}, "seq_regions": {}, "phenotypes": {},
    })
    def antigen(gene: str, serotype: str) -> dict:
        return {"gene": gene, "serotype": serotype, "accession": "NA",
                "position_in_ref": "1..100", "template_length": 100, "HSP_length": 100,
                "identity": 99.0, "coverage": 100.0}
    write_json(cases / "serotypefinder.json", {"serotypefinder": {"results": {
        "O_type": {"hit1": antigen("wzx", "O157")},
        "H_type": {"hit1": antigen("fliC", "H7")},
    }}})
    write_text(cases / "malformed.json", "{this is deliberately invalid json\n")
    write_text(cases / "samtools-empty.stats", "# No stats produced\n")


def write_resource_inputs() -> None:
    """One shared reference and a tiny SAM; optional tool step builds BAM/indexes."""
    resources = FIXTURE_ROOT / "resources"
    sequence = deterministic_dna("bonsai-local-test:mtuberculosis", GENOME_LENGTH)
    write_fasta(resources / "reference.fasta", REFERENCE_NAME, sequence)
    sam = ["@HD\tVN:1.6\tSO:coordinate", f"@SQ\tSN:{REFERENCE_NAME}\tLN:{GENOME_LENGTH}"]
    for number in range(20):
        start = 1900 + number * 20
        read = sequence[start:start + 100]
        sam.append(f"synthetic-read-{number:03d}\t0\t{REFERENCE_NAME}\t{start + 1}\t60\t100M\t*\t0\t0\t{read}\t{'I' * 100}")
    write_text(resources / "alignment.sam", "\n".join(sam) + "\n")
    write_text(resources / "annotation.bed", f"{REFERENCE_NAME}\t1900\t2400\tsynthetic_locus\n")
    genomes = FIXTURE_ROOT / "cases/genomes"
    for name, genome in (
        ("synthetic_identical", sequence),
        ("synthetic_unrelated", deterministic_dna("bonsai-local-test:unrelated", GENOME_LENGTH)),
        ("synthetic_deletion", sequence[:20_000] + sequence[24_000:]),
    ):
        write_fasta(genomes / f"{name}.fasta", name, genome)
    write_text(FIXTURE_ROOT / "cases/gap_alignment.fasta", ">reference\nAACCGGTT\n>deletion\nAAC--GTT\n")
    write_text(FIXTURE_ROOT / "cases/chewbbaca-missing.out", "FILE\tSYNLOC0001\tSYNLOC0002\tSYNLOC0003\nsynthetic_missing\tLNF\tINF-2\t1\n")


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
        "lims_id": f"SYNTHETIC-LIMS-{assay.upper()}-{sample_number:03d}",
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
    else:
        analysis += """  - software: mykrobe
    software_version: 0.12.2
    uri: mykrobe.csv
  - software: postalignqc
    software_version: 1.0.0
    uri: postalignqc.json
"""
        if sample_number != 10:
            analysis += """  - software: tbprofiler
    software_version: 6.3.0
    uri: tbprofiler.json
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
        if not include_allele_profiles:
            write_extended_results(sample_dir, sample_id, sample_number)
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
    write_typing_cases()
    write_resource_inputs()
    print(f"Generated {SAMPLE_COUNT * 2} samples under {SAMPLE_ROOT}")


if __name__ == "__main__":
    main()
