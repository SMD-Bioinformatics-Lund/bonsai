"""Test clustering related functions."""

import pytest
from Bio.Align import MultipleSeqAlignment
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

from ska_service.ska.cluster import calc_snv_distance


@pytest.mark.parametrize(
    "seq_a,seq_b,ignore_gaps,exp_dist",
    [
        ("AAAA", "AAAT", False, 1),
        ("A-AA", "AAAA", False, 1),
        ("A-AA", "AAAA", True, 0),
    ],
)
def test_calc_snv_distance_wo_ignore_gaps(seq_a, seq_b, ignore_gaps, exp_dist):
    """Test calculating SNV distance."""

    aln = MultipleSeqAlignment(
        [
            SeqRecord(Seq(seq_a), id="A", name="A"),
            SeqRecord(Seq(seq_b), id="B", name="B"),
        ]
    )

    dm = calc_snv_distance(aln, ignore_gaps=ignore_gaps)

    assert dm["A", "B"] == exp_dist
