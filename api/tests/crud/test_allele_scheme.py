"""Compatibility uses producing profiles and, for MLST, detected schemes."""

import asyncio
from types import SimpleNamespace

import mongomock
import pytest

from bonsai_api.crud.allele_scheme import get_profile_scheme, validate_typing_schemes
from bonsai_api.crud.cluster import get_typing_profiles, TypingProfileAggregate
from bonsai_api.exceptions import EntryNotFound, InvalidDataFormat


def stored(sid, scheme="same", alleles=None, method="mlst", assay="same", **extra):
    return {
        "sample_id": sid,
        "typing_result": [
            {
                "software": "mlst" if method == "mlst" else "chewbbaca",
                "analysis_type": method,
                "status": "parsed",
                "pipeline_run_id": "run",
                "result": {
                    "scheme": scheme,
                    "alleles": alleles if alleles is not None else {"x": 1, "y": "LNF"},
                },
                **extra,
            }
        ],
        "pipeline_runs": [{"pipeline_run_id": "run", "assay": assay}],
    }


def validate(samples, method="mlst", ids=None):
    collection = mongomock.MongoClient().db.samples
    collection.insert_many(samples)

    async def records(rows):
        for row in rows:
            yield row

    async def aggregate(pipeline):
        # mongomock cannot unset temporary selection fields; run all other stages.
        return records(
            list(collection.aggregate([s for s in pipeline if "$unset" not in s]))
        )

    db = SimpleNamespace(sample_collection=SimpleNamespace(aggregate=aggregate))
    profiles = asyncio.run(
        get_typing_profiles(db, ids or [s["sample_id"] for s in samples], method)
    )
    return validate_typing_schemes(profiles, method)


@pytest.mark.parametrize("method", ["mlst", "cgmlst"])
def test_matching_full_locus_sets_allow_missing_calls(method):
    assert validate(
        [
            stored("a", method=method),
            stored("b", alleles={"y": 2, "x": "LNF"}, method=method),
        ],
        method,
    ).can_cluster


@pytest.mark.parametrize("method", ["mlst", "cgmlst"])
def test_different_identities_are_blocked(method):
    identity = "analysis profiles" if method == "cgmlst" else "typing schemes"
    result = validate(
        [
            stored("a", method=method),
            stored("b", "other", method=method, assay="other"),
        ],
        method,
    )
    assert not result.can_cluster
    assert f"different {identity}" in result.notice
    if method == "cgmlst":
        assert "locus" not in result.notice.lower()


@pytest.mark.parametrize("method", ["mlst", "cgmlst"])
def test_unknown_identity_blocks_even_when_locus_names_match(method):
    result = validate(
        [stored(sid, None, method=method, assay=None) for sid in ["a", "b"]], method
    )
    assert not result.can_cluster
    assert "could not be verified" in result.notice


def test_missing_database_sample_is_not_considered_compatible():
    with pytest.raises(EntryNotFound):
        validate([stored("a")], ids=["a", "missing"])


def test_empty_profiles_are_reported_as_missing_typing_data():
    profiles = [
        TypingProfileAggregate(
            sample_id="a", scheme="same", assay="same", typing_result={"x": 1}
        ),
        TypingProfileAggregate(
            sample_id="empty", scheme="same", assay="same", typing_result={}
        ),
    ]
    result = validate_typing_schemes(profiles, "mlst")
    assert not result.can_cluster
    assert "typing data is unavailable for 1 sample" in result.notice
    assert result.groups[0].sample_ids == ["empty"]


def test_cgmlst_identity_uses_profile_from_the_selected_analysis_run():
    raw = {
        "typing_pipeline_run_id": "older",
        "pipeline_runs": [
            {
                "pipeline_run_id": "newer",
                "assay": "saureus",
            },
            {
                "pipeline_run_id": "older",
                "assay": "ecoli",
            },
        ],
    }
    assert get_profile_scheme(raw, "cgmlst") == "ecoli"
    raw["typing_pipeline_run_id"] = "unknown"
    assert get_profile_scheme(raw, "cgmlst") is None


def test_cgmlst_uses_selected_analysis_and_its_producing_profile():
    a = stored(
        "a",
        scheme=None,
        method="cgmlst",
        pipeline_run_id="run-1",
        meta={"scheme": "declared"},
    )
    a["typing_result"].insert(
        0,
        {
            "software": "chewbbaca",
            "analysis_type": "other",
            "result": {"scheme": "wrong", "alleles": {"wrong": 99}},
        },
    )
    b = stored(
        "b",
        scheme=None,
        method="cgmlst",
        pipeline_run_id="run-1",
        meta={"scheme": "declared"},
    )
    for sample in (a, b):
        sample["pipeline_runs"] = [
            {
                "pipeline_run_id": "newest",
                "assay": "saureus",
            },
            {
                "pipeline_run_id": "run-1",
                "assay": "ecoli",
            },
        ]
    assert validate([a, b], "cgmlst").can_cluster
    # A shared latest assay must not hide different producing assays.
    b["pipeline_runs"][1]["assay"] = "staphylococcus"
    result = validate([a, b], "cgmlst")
    assert not result.can_cluster
    assert "different analysis profiles" in result.notice


def test_cgmlst_profile_is_sufficient_without_scheme_or_database_metadata():
    samples = [
        stored(sid, scheme=None, method="cgmlst", assay="ecoli")
        for sid in ["a", "b"]
    ]
    assert validate(samples, "cgmlst").can_cluster


def test_cgmlst_metadata_versions_do_not_split_a_shared_analysis_profile():
    samples = [
        stored(sid, scheme=sid, method="cgmlst", assay="ecoli", software_version=sid)
        for sid in ["a", "b"]
    ]
    for sample in samples:
        sample["pipeline_runs"][0]["pipeline_info"] = {
            "databases": [
                {
                    "software": "chewbbaca",
                    "name": sample["sample_id"],
                    "version": sample["sample_id"],
                }
            ]
        }
    assert validate(samples, "cgmlst").can_cluster


@pytest.mark.parametrize("assay", [None, "", "  ", 42, ["ecoli"]])
@pytest.mark.parametrize("method", ["mlst", "cgmlst"])
def test_unknown_profile_is_not_replaced_by_scheme_or_database(assay, method):
    a = stored("a", method=method, assay="ecoli")
    b = stored("b", method=method, assay=assay)
    for sample in (a, b):
        sample["pipeline_runs"][0]["pipeline_info"] = {
            "databases": [{"software": "chewbbaca", "name": "shared", "version": "1"}]
        }
    result = validate([a, b], method)
    assert not result.can_cluster
    assert "analysis profile could not be verified" in result.notice


@pytest.mark.parametrize(
    "provenance", ["missing_run_id", "unknown_run_id", "no_runs", "duplicate_runs"]
)
@pytest.mark.parametrize("method", ["mlst", "cgmlst"])
def test_requires_an_unambiguous_producing_run(provenance, method):
    a = stored("a", method=method, assay="ecoli")
    b = stored("b", method=method, assay="ecoli")
    b["last_pipeline_run_id"] = "run"
    if provenance == "missing_run_id":
        del b["typing_result"][0]["pipeline_run_id"]
    elif provenance == "unknown_run_id":
        b["typing_result"][0]["pipeline_run_id"] = "unknown"
    elif provenance == "no_runs":
        b["pipeline_runs"] = []
    else:
        b["pipeline_runs"].append(dict(b["pipeline_runs"][0]))
    result = validate([a, b], method)
    assert not result.can_cluster
    assert "analysis profile could not be verified" in result.notice


def test_mlst_matching_schemes_cannot_cross_analysis_profiles():
    result = validate(
        [
            stored("a", scheme="spneumoniae", assay="streptococcus"),
            stored("b", scheme="spneumoniae", assay="spneumoniae"),
        ]
    )
    assert not result.can_cluster
    assert "different analysis profiles" in result.notice


def test_mlst_assay_comes_from_selected_result_not_the_latest_run():
    samples = [stored(sid, assay="streptococcus") for sid in ["a", "b"]]
    for sample in samples:
        sample["pipeline_runs"].insert(
            0, {"pipeline_run_id": "newest", "assay": "spneumoniae"}
        )
        sample["last_pipeline_run_id"] = "newest"
    assert validate(samples).can_cluster
    # A shared latest assay must not hide different producing assays.
    samples[1]["pipeline_runs"][1]["assay"] = "spneumoniae"
    result = validate(samples)
    assert not result.can_cluster
    assert "different analysis profiles" in result.notice


def test_mlst_same_broad_profile_cannot_mix_detected_schemes():
    result = validate(
        [
            stored("a", scheme="spneumoniae", assay="streptococcus"),
            stored("b", scheme="spyogenes", assay="streptococcus"),
        ]
    )
    assert not result.can_cluster
    assert "different typing schemes" in result.notice


def test_mlst_unknown_scheme_cannot_use_the_analysis_profile():
    result = validate(
        [
            stored("a", scheme="spneumoniae", assay="streptococcus"),
            stored("b", scheme=None, assay="streptococcus"),
        ]
    )
    assert not result.can_cluster
    assert "typing scheme could not be verified" in result.notice


def test_mlst_scheme_can_come_from_selected_analysis_metadata():
    assert validate(
        [
            stored(sid, scheme=None, meta={"scheme": "spneumoniae"})
            for sid in ["a", "b"]
        ]
    ).can_cluster


@pytest.mark.parametrize("sample_name", [None, "", "CARD-123"])
def test_unknown_scheme_details_identify_only_affected_samples(sample_name):
    samples = [stored("a"), stored("b", scheme=None)]
    samples[1]["external_sample_id"] = "LAB-123"
    samples[1]["sample_name"] = sample_name
    result = validate(samples)
    label = sample_name or "LAB-123"
    assert result.details == [f"No detected MLST scheme is available:\n{label}"]


@pytest.mark.parametrize("method", ["mlst", "cgmlst"])
def test_different_identities_include_values_and_affected_samples(method):
    result = validate(
        [
            stored("a", scheme="ecoli", assay="ecoli", method=method),
            stored("b", scheme="saureus", assay="staphylococcus", method=method),
        ],
        method,
    )
    assert not result.can_cluster
    assert any("ecoli — 1 sample:\na" in detail for detail in result.details)
    other = "staphylococcus" if method == "cgmlst" else "saureus"
    assert any(f"{other} — 1 sample:\nb" in detail for detail in result.details)


def test_mlst_different_schemes_do_not_repeat_samples_under_locus_sets():
    samples = [
        stored("a", scheme="spneumoniae", alleles={"x": 1, "y": 2}),
        stored("b", scheme="spyogenes", alleles={"x": 1, "z": 2}),
        stored("c", scheme="spneumoniae", alleles={"x": 2, "y": 3}),
    ]
    result = validate(samples)
    assert not result.can_cluster
    assert "Select samples from one scheme" in result.notice
    assert "locus" not in result.notice
    assert result.details == [
        "spneumoniae — 2 samples:\na\nc",
        "spyogenes — 1 sample:\nb",
    ]
    # Keeping just one scheme still checks its locus definitions.
    samples[2]["typing_result"][0]["result"]["alleles"] = {"x": 2, "z": 3}
    assert not validate([samples[0], samples[2]]).can_cluster


@pytest.mark.parametrize(
    "alleles", [{"x": 1}, {"x": 1, "z": 2}, {"x": 1, "y": 2, "z": 3}]
)
def test_cgmlst_shared_analysis_profile_assumes_compatible_loci(alleles):
    result = validate(
        [
            stored("a", method="cgmlst"),
            stored("b", alleles=alleles, method="cgmlst"),
        ],
        "cgmlst",
    )
    assert result.can_cluster
    assert not result.notice
    assert not result.details


def test_mlst_locus_details_distinguish_equal_sized_but_different_sets():
    shared_loci = dict.fromkeys(["spi", "recP", "gki", "gdh", "ddl", "aroE"], 1)
    result = validate(
        [
            stored("a", alleles={**shared_loci, "xpt": 2}),
            stored("b", alleles={**shared_loci, "zpt": 2}),
        ],
    )
    assert not result.can_cluster
    assert "share a typing scheme but have different locus sets" in result.notice
    assert "same locus definitions" in result.notice
    assert result.details == [
        "Locus set 1 (7 loci; aroE, ddl, gdh, gki, recP, spi, xpt):\na",
        "Locus set 2 (7 loci; aroE, ddl, gdh, gki, recP, spi, zpt):\nb",
    ]


@pytest.mark.parametrize("alleles", [[1, 2], {"x": "INF"}])
def test_malformed_allele_profiles_report_the_affected_lab_id(alleles):
    sample = stored("a", alleles=alleles)
    sample["external_sample_id"] = "LAB-123"
    with pytest.raises(InvalidDataFormat, match="Invalid MLST allele profile for LAB-123"):
        validate([sample])


@pytest.mark.parametrize(
    "field,missing,method",
    [
        ("scheme", False, "mlst"),
        ("assay", False, "mlst"),
        ("loci", False, "mlst"),
        ("scheme", False, "cgmlst"),
        ("scheme", True, "mlst"),
        ("assay", True, "mlst"),
        ("scheme", True, "cgmlst"),
    ],
)
@pytest.mark.parametrize("label_field", ["sample_name", "external_sample_id"])
def test_notice_sample_groups_show_five_labels_and_remaining_count(
    field, missing, method, label_field
):
    profiles = [
        TypingProfileAggregate(
            sample_id=f"internal-{i}",
            **{"external_sample_id": f"EXTERNAL-{i:02}", label_field: f"LABEL-{i:02}"},
            scheme="same", assay="same", typing_result={"x": 1},
        )
        for i in reversed(range(25))
    ]
    if missing:
        for profile in profiles:
            setattr(profile, field, None)
    else:
        other = TypingProfileAggregate(
            sample_id="other", scheme="same", assay="same", typing_result={"x": 1},
        )
        if field == "loci":
            other.typing_result = {"y": 1}
        else:
            setattr(other, field, "other")
        profiles.append(other)
    result = validate_typing_schemes(profiles, method)
    assert not result.can_cluster
    detail = next(detail for detail in result.details if "LABEL-00" in detail)
    assert "LABEL-00\nLABEL-01\nLABEL-02\nLABEL-03\nLABEL-04\nand 20 more" in detail
    assert "LABEL-05" not in detail
    assert "LABEL-24" not in detail
    assert "EXTERNAL-" not in detail
    assert "internal-" not in detail
    group = next(group for group in result.groups if group.detail == detail)
    assert set(group.sample_ids) == {f"internal-{i}" for i in range(25)}
    if field in {"scheme", "assay"} and not missing:
        assert "25 samples" in detail


@pytest.mark.parametrize("count", [5, 6])
def test_missing_scheme_notices_count_only_ids_beyond_five(count):
    result = validate([stored(f"sample-{i}", scheme=None) for i in range(count)])
    assert len(result.details) == 1
    assert "sample-0\nsample-1\nsample-2\nsample-3\nsample-4" in result.details[0]
    if count == 5:
        assert "more" not in result.details[0]
    else:
        assert result.details[0].endswith("\nand 1 more")
        assert "sample-5" not in result.details[0]


def test_missing_typing_profiles_limit_ids_in_the_unavailable_data_notice():
    samples = [stored(f"internal-{i}", alleles={}) for i in reversed(range(25))]
    for sample in samples:
        sample["external_sample_id"] = f"LAB-{int(sample['sample_id'].split('-')[1]):02}"
    with pytest.raises(EntryNotFound) as error:
        validate(samples)
    message = str(error.value)
    assert "LAB-00\nLAB-01\nLAB-02\nLAB-03\nLAB-04\nand 20 more" in message
    assert "LAB-05" not in message
    assert "LAB-24" not in message


@pytest.mark.parametrize("method", ["mlst", "cgmlst"])
@pytest.mark.parametrize("alleles", [{}, [1, 2], {"x": "INF"}])
def test_typing_data_errors_use_the_basket_card_name(method, alleles):
    sample = stored("internal-123", alleles=alleles, method=method)
    sample.update(sample_name="CARD-123", external_sample_id="LAB-123")
    with pytest.raises((EntryNotFound, InvalidDataFormat)) as error:
        validate([sample], method)
    assert "CARD-123" in str(error.value)
    assert "LAB-123" not in str(error.value)
    assert "internal-123" not in str(error.value)
