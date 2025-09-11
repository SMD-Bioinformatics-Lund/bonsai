"""Test IO functions."""

from bonsai_api.io import TARGETED_ANTIBIOTICS, lims_rs_formatter, sample_to_kmlims


def test_mtb_kmlims_export(mtuberculosis_sample):
    """Test export mtuberculosis kmlims export."""
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
    assert len(result) == n_exp_antibiotics + 3  # + lineage, qc, and spp pred

    # test that valid parameter codes are used
    VALID_PARAMS = (
        "RIF_NGS",
        "INH_NGSH",
        "INH_NGSL",
        "PYR_NGS",
        "ETB_NGS",
        "AMI_NGS",
        "LEV_NGS",
        "MTBC_QC",
        "MTBC_ART",
        "MTBC_LINEAGE",
    )
    matched_params = (
        result.assign(
            matched=lambda col: col["parameter"].apply(
                lambda param: param in VALID_PARAMS
            )
        )
        .set_index("parameter")
        .loc[:, "matched"]
    )
    assert matched_params.all()
