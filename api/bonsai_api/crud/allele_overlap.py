"""Reject distances without any jointly observed allele calls."""

from itertools import combinations

from bonsai_api.crud.cluster import TypingProfileOutput
from bonsai_api.exceptions import InvalidDataFormat


def validate_allele_overlap(profiles: TypingProfileOutput, typing_method: str) -> None:
    """Every pair of usable samples must share at least one called locus."""
    called_loci = [
        {
            gene
            for gene, value in profile.allele_profile().items()
            if type(value) is int and value > 0
        }
        for profile in profiles
    ]
    # Profiles without usable calls belong to sample accounting, not distances.
    called_loci = [loci for loci in called_loci if loci]
    if any(a.isdisjoint(b) for a, b in combinations(called_loci, 2)):
        name = "cgMLST" if typing_method == "cgmlst" else "MLST"
        raise InvalidDataFormat(
            f"Cannot cluster by {name}: some sample pairs have no jointly called loci. "
            "A genetic distance cannot be assigned to those pairs."
        )
