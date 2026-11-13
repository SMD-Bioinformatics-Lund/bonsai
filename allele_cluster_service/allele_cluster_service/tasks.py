"""Define reddis tasks."""

import logging
import csv
import io
from collections import Counter

from ete3 import Tree

from .ms_trees import ClusterMethod, backend

LOG = logging.getLogger(__name__)


def cluster(profile: str, method: str, sample_ids: list[str] | None = None) -> str:
    """
    Cluster multiple sample on their allele profiles.

    :param profile str: a string representation of a tsv table of the allele profiles
    :param method str: the MStree clustering method

    :raises ValueError: raises an exception if the method is not a valid MSTree clustering method.

    :return: cluster in newick format
    :rtype: str
    """
    try:
        method = ClusterMethod(method)
    except ValueError as error:
        msg = f'"{method}" is not a valid cluster method'
        LOG.error(msg)
        raise ValueError(msg) from error
    if sample_ids is not None:
        if not sample_ids:
            raise ValueError("No expected samples were supplied")
        if len(sample_ids) != len(set(sample_ids)):
            raise ValueError("Expected sample IDs must be unique")
        rows = list(csv.reader(io.StringIO(profile), delimiter="\t"))
        if not rows or len(rows[0]) < 2:
            raise ValueError("No allele columns are available for clustering")
        data = [row for row in rows[1:] if row]
        if Counter(row[0] for row in data) != Counter(sample_ids):
            raise ValueError(
                "The allele table does not contain every expected sample exactly once"
            )
        for row in data:
            if len(row) != len(rows[0]):
                raise ValueError(f"Incomplete allele row for sample {row[0]}")
            if not any(call not in {"", "-", "0", "0.0", "N"} for call in row[1:]):
                raise ValueError(f"Sample has no usable allele calls: {row[0]}")
        if len(sample_ids) == 1:
            tree = Tree()
            tree.add_child(name=sample_ids[0], dist=0)
            return tree.write(format=1)
    newick = backend(profile=profile, method=method.value)
    if sample_ids is not None and Counter(Tree(newick).get_leaf_names()) != Counter(
        sample_ids
    ):
        raise ValueError(
            "The allele tree does not contain every expected sample exactly once"
        )
    return newick
