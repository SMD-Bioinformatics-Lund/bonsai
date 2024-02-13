"""Test IO functions."""

from app.io import sample_to_kmlims, TARGETED_ANTIBIOTICS


def test_sample_to_kmlims(mtuberculosis_sample):
    """Test export sample to kmlims."""
    result = sample_to_kmlims(sample=mtuberculosis_sample)

    # test that,
    # six variants were reported
    assert len(result) == len(TARGETED_ANTIBIOTICS)

    # two found variants with resistance
    n_resistance = len(result.query("result == 'Mutation påvisad'"))
    assert n_resistance == 2