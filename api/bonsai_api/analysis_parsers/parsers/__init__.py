"""Parse output of softwares in pipeline."""

from .qc import (
    parse_alignment_results,
    parse_gambitcore_results,
    parse_postalignqc_results,
    parse_quast_results,
)
from .sample import parse_sample
from .typing import parse_cgmlst_results, parse_mlst_results
from .variant import load_variants
