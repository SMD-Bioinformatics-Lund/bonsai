"""Functions for clustering using a distance matrix."""

import itertools
import logging
from typing import Any, Sequence

from Bio.Align import MultipleSeqAlignment
from Bio.Phylo.TreeConstruction import DistanceMatrix as BioDistanceMatrix

LOG = logging.getLogger(__name__)

TreeObj = tuple[None, Any] | Any | None


class DistanceMatrix(BioDistanceMatrix):
    """Extended version of the DistanceMatrix from Biopython."""

    def to_condensed(self) -> Sequence[float | int]:
        """Convert to condensed distance matrix compatible with scipy linkage."""
        return [
            self.__getitem__((seq1, seq2))
            for seq1, seq2 in itertools.combinations(self.names, 2)
        ]

def calc_snv_distance(
    aln: MultipleSeqAlignment, *, ignore_gaps: bool = False
) -> DistanceMatrix:
    """Calculate pair-wise sample distance from aligned fasta sequences."""

    def _valid_pair(a: str, b: str, *, ignore_gaps: bool) -> bool:
        return not ignore_gaps or (a != "-" and b != "-")

    dm = DistanceMatrix(names=[al.name for al in aln])
    for seq1, seq2 in itertools.combinations(aln, 2):
        n_different = sum(
            seq_a != seq_b
            for seq_a, seq_b in zip(seq1, seq2)
            if _valid_pair(seq_a, seq_b, ignore_gaps=ignore_gaps)
        )
        dm[seq1.name, seq2.name] = n_different
    return dm