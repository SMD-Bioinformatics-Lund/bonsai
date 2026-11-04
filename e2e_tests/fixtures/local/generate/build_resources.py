#!/usr/bin/env python3
"""Build real indexed resources from the small generated FASTA and SAM."""
from pathlib import Path

import pysam

root = Path(__file__).resolve().parents[1] / "resources"
pysam.faidx(str(root / "reference.fasta"))
pysam.sort("-o", str(root / "alignment.bam"), str(root / "alignment.sam"))
pysam.index(str(root / "alignment.bam"))
with pysam.AlignmentFile(str(root / "alignment.bam")) as bam:
    assert bam.has_index() and bam.count() == 20
with pysam.FastaFile(str(root / "reference.fasta")) as fasta:
    assert fasta.lengths == [100_000]
print("PASS resources: indexed 100 kb reference and 20-read BAM")
