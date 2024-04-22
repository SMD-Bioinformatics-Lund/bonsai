"""Test IO functions."""

from app.io import TARGETED_ANTIBIOTICS, sample_to_kmlims


def test_sample_to_kmlims(mtuberculosis_sample):
    """Test export sample to kmlims."""
    result = sample_to_kmlims(sample=mtuberculosis_sample)

    # filter out lineage and spp pred from result
    n_exp_antibiotics = sum(
        [
            2 if antib["split_res_level"] else 1
            for antib in TARGETED_ANTIBIOTICS.values()
        ]
    )
    # test that,
    # the targeted antibiotics were reported
    assert len(result) == n_exp_antibiotics + 2  # + lineage and spp pred
