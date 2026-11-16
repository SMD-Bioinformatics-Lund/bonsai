"""Compatibility uses detected MLST schemes or producing cgMLST profiles."""

import asyncio
from types import SimpleNamespace

import mongomock
import pytest

from bonsai_api.crud.allele_scheme import get_profile_scheme, validate_typing_schemes
from bonsai_api.crud.cluster import get_typing_profiles, TypingProfileAggregate
from bonsai_api.exceptions import EntryNotFound


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
def test_different_schemes_or_locus_sets_are_blocked(method):
    identity = "analysis profiles" if method == "cgmlst" else "typing schemes"
    for second in [
        stored("b", "other", method=method, assay="other"),
        stored("b", alleles={"x": 1, "z": "LNF"}, method=method),
    ]:
        result = validate([stored("a", method=method), second], method)
        assert not result.can_cluster
        assert f"different {identity} or locus sets" in result.notice


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


def test_empty_profiles_do_not_supply_locus_evidence_for_unplaced_samples():
    profiles = [
        TypingProfileAggregate(sample_id="a", scheme="same", typing_result={"x": 1}),
        TypingProfileAggregate(sample_id="empty", scheme="same", typing_result={}),
    ]
    assert validate_typing_schemes(profiles, "mlst").can_cluster


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
def test_cgmlst_unknown_profile_is_not_replaced_by_scheme_or_database(assay):
    a = stored("a", method="cgmlst", assay="ecoli")
    b = stored("b", method="cgmlst", assay=assay)
    for sample in (a, b):
        sample["pipeline_runs"][0]["pipeline_info"] = {
            "databases": [{"software": "chewbbaca", "name": "shared", "version": "1"}]
        }
    result = validate([a, b], "cgmlst")
    assert not result.can_cluster
    assert "analysis profile could not be verified" in result.notice


@pytest.mark.parametrize(
    "provenance", ["missing_run_id", "unknown_run_id", "no_runs", "duplicate_runs"]
)
def test_cgmlst_requires_an_unambiguous_producing_run(provenance):
    a = stored("a", method="cgmlst", assay="ecoli")
    b = stored("b", method="cgmlst", assay="ecoli")
    b["last_pipeline_run_id"] = "run"
    if provenance == "missing_run_id":
        del b["typing_result"][0]["pipeline_run_id"]
    elif provenance == "unknown_run_id":
        b["typing_result"][0]["pipeline_run_id"] = "unknown"
    elif provenance == "no_runs":
        b["pipeline_runs"] = []
    else:
        b["pipeline_runs"].append(dict(b["pipeline_runs"][0]))
    result = validate([a, b], "cgmlst")
    assert not result.can_cluster
    assert "analysis profile could not be verified" in result.notice


def test_mlst_matching_schemes_can_cross_analysis_profiles():
    assert validate(
        [
            stored("a", scheme="spneumoniae", assay="streptococcus"),
            stored("b", scheme="spneumoniae", assay="spneumoniae"),
        ]
    ).can_cluster


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
