"""Functions for clustering using a distance matrix."""

import itertools
import logging
from typing import Any, Sequence

from Bio.Align import MultipleSeqAlignment
from Bio.Phylo.TreeConstruction import DistanceMatrix as BioDistanceMatrix
from bonsai_libs.clustering import hierarchical_clustering, minimum_spanning_tree_clustering, LinkageMethod

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


def cluster_alignment(
    aln: MultipleSeqAlignment,
    sample_ids: Sequence[str],
    *,
    algorithm: str,
    method: LinkageMethod | None = None,
) -> str:
    dm = calc_snv_distance(aln)
    condensed = dm.to_condensed()

    if algorithm == "hierarchical":
        result = hierarchical_clustering(
            condensed,
            sample_ids,
            method=method,
        )
    elif algorithm == "mst":
        result = minimum_spanning_tree_clustering(
            condensed,
            sample_ids,
        )
    else:
        raise ValueError(f"Unknown clustering algorithm: {algorithm}")

    return result.to_newick()
