"""Missing overlap is not evidence of zero distance."""

import pytest

from bonsai_api.crud.allele_overlap import validate_allele_overlap
from bonsai_api.crud.cluster import TypingProfileAggregate
from bonsai_api.exceptions import InvalidDataFormat


def profile(sid, calls):
    return TypingProfileAggregate(sample_id=sid, typing_result=calls)


@pytest.mark.parametrize("method", ["mlst", "cgmlst"])
def test_zero_overlap_is_rejected_even_if_a_third_sample_overlaps_both(method):
    samples = [
        profile("a", {"x": 1, "y": None}),
        profile("b", {"x": None, "y": 1}),
        profile("c", {"x": 1, "y": 1}),
    ]
    with pytest.raises(InvalidDataFormat, match="no jointly called loci"):
        validate_allele_overlap(samples, method)


@pytest.mark.parametrize("missing", [0, None, "LNF", "-", False])
def test_missing_calls_do_not_establish_overlap(missing):
    with pytest.raises(InvalidDataFormat, match="no jointly called loci"):
        validate_allele_overlap(
            [
                profile("a", {"x": 1, "y": missing}),
                profile("b", {"x": missing, "y": 2}),
            ],
            "mlst",
        )


def test_shared_calls_may_agree_or_differ():
    for value in [1, 2]:
        validate_allele_overlap(
            [profile("a", {"x": 1, "y": None}), profile("b", {"x": value, "y": 3})],
            "mlst",
        )


def test_unplaced_samples_are_not_compared_as_if_they_had_distances():
    validate_allele_overlap(
        [profile("a", {"x": 1}), profile("empty", {"x": None})], "cgmlst"
    )
