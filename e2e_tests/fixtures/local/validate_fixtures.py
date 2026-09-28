#!/usr/bin/env python3
"""Validate generated reports against the installed, pinned Bonsai SDK.

Run in the API image; no running stack or database is required.
"""
from pathlib import Path

from bonsai_libs.parse import run_parser

from generate.generate_fixtures import SAMPLE_COUNT

ROOT = Path(__file__).resolve().parent


def parse(software, filename, version, **kwargs):
    result = run_parser(software=software, version=version, data=filename, **kwargs)
    errors = {str(key): env.reason for key, env in result.results.items()
              if str(env.status) == "error"}
    assert not errors, (filename, errors)
    return result.results


def main():
    for number in range(1, SAMPLE_COUNT + 1):
        tb = ROOT / "samples" / f"synthetic_tb_{number:03d}"
        sa = ROOT / "samples" / f"synthetic_sa_{number:03d}"
        for folder in (tb, sa):
            assert str(parse("bracken", folder / "bracken.out", "2.8.0")["species_prediction"].status) == "parsed"
            assert parse("quast", folder / "quast.tsv", "5.2.0")["qc"].value.total_length == 100_000
        assert str(parse("mlst", sa / "mlst.json", "2.23.0")["mlst"].value.sequence_type) == str(100 + number)
        assert str(parse("chewbbaca", sa / "chewbbaca.out", "3.3.10")["cgmlst"].status) == "parsed"
        amr = parse("tbprofiler", tb / "tbprofiler.json", "6.3.0")
        assert amr["lineage"].value[0].lineage == "lineage2.2.1"
        if number == 2:
            assert str(amr["amr"].status) == "absent"
        else:
            assert len(amr["amr"].value.variants) == 3
            assert [v.passed_qc for v in amr["amr"].value.variants].count(False) == 1
        mykrobe = parse("mykrobe", tb / "mykrobe.csv", "0.12.2")["amr"].value
        assert len(mykrobe.variants) == (0 if number == 2 else 1)
        qc = parse("postalignqc", tb / "postalignqc.json", "1.0.0")["qc"].value
        stats = parse("samtools", tb / "samtools.stats", "1.21", subcommand="stats",
                      coverage_path=tb / "samtools.coverage", bedcov_path=tb / "samtools.bedcov")["qc"].value
        assert stats.model_dump() == qc.model_dump(), (stats, qc)
        partial = parse("samtools", tb / "samtools.stats", "1.21", subcommand="stats")["qc"].value
        assert partial.n_reads == 1000 and partial.mean_cov is None
        assert str(parse("samtools", tb / "samtools.coverage", "1.21", subcommand="coverage")["qc"].status) == "parsed"
    vir = parse("virulencefinder", ROOT / "cases/virulencefinder.json", "3.0.0")
    assert vir["virulence"].value.genes[0].gene_symbol == "synthetic_vir"
    assert vir["stx"].value.gene_symbol == "stx2a"
    empty = parse("virulencefinder", ROOT / "cases/virulencefinder-empty.json", "3.0.0")
    assert empty["virulence"].value.genes == []
    serotype = parse("serotypefinder", ROOT / "cases/serotypefinder.json", "2.0.0")
    assert serotype["o_type"].value.sequence_name == "O157"
    assert serotype["h_type"].value.sequence_name == "H7"
    missing = parse("chewbbaca", ROOT / "cases/chewbbaca-missing.out", "3.3.10")["cgmlst"].value
    assert missing.n_missing == 1 and missing.n_novel == 1
    assert str(parse("samtools", ROOT / "cases/samtools-empty.stats", "1.21", subcommand="stats")["qc"].status) == "empty"
    try:
        result = run_parser(software="tbprofiler", version="6.3.0", data=ROOT / "cases/malformed.json")
    except ValueError:
        pass
    else:
        assert any(str(env.status) == "error" for env in result.results.values())
    print(f"PASS reports: {SAMPLE_COUNT * 2} samples, AMR/lineage, QC auxiliary inputs, virulence/STX and serotype cases")


if __name__ == "__main__":
    main()
