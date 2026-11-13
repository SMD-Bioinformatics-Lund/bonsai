"""Scheme compatibility uses complete locus sets and selected-run provenance."""

import asyncio
from types import SimpleNamespace

import mongomock
import pytest

from bonsai_api.crud.allele_scheme import get_profile_scheme, validate_typing_schemes
from bonsai_api.crud.cluster import get_typing_profiles, TypingProfileAggregate
from bonsai_api.exceptions import EntryNotFound


def stored(sid, scheme="same", alleles=None, method="mlst", **extra):
    return {
        "sample_id": sid,
        "typing_result": [
            {
                "software": "mlst" if method == "mlst" else "chewbbaca",
                "analysis_type": method,
                "status": "parsed",
                "result": {
                    "scheme": scheme,
                    "alleles": alleles if alleles is not None else {"x": 1, "y": "LNF"},
                },
                **extra,
            }
        ],
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
    for second in [
        stored("b", "other", method=method),
        stored("b", alleles={"x": 1, "z": "LNF"}, method=method),
    ]:
        result = validate([stored("a", method=method), second], method)
        assert not result.can_cluster
        assert "different typing schemes or locus sets" in result.notice


@pytest.mark.parametrize("method", ["mlst", "cgmlst"])
def test_unknown_identity_blocks_even_when_locus_names_match(method):
    result = validate(
        [stored("a", None, method=method), stored("b", None, method=method)], method
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


def test_cgmlst_identity_uses_database_from_the_selected_analysis_run():
    raw = {
        "typing_pipeline_run_id": "older",
        "pipeline_runs": [
            {
                "pipeline_run_id": "newer",
                "pipeline_info": {
                    "databases": [
                        {"software": "chewbbaca", "name": "other", "version": "2"}
                    ]
                },
            },
            {
                "pipeline_run_id": "older",
                "pipeline_info": {
                    "databases": [
                        {"software": "chewbbaca", "name": "expected", "version": "1"}
                    ]
                },
            },
        ],
    }
    assert get_profile_scheme(raw, "cgmlst") == '[null,"expected","1"]'
    raw["typing_pipeline_run_id"] = "unknown"
    assert get_profile_scheme(raw, "cgmlst") is None


def test_cgmlst_uses_selected_analysis_and_database_version():
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
                "pipeline_info": {
                    "databases": [
                        {"software": "chewbbaca", "name": "wrong", "version": "9"}
                    ]
                },
            },
            {
                "pipeline_run_id": "run-1",
                "pipeline_info": {
                    "databases": [
                        {"software": "chewbbaca", "name": "expected", "version": "1"}
                    ]
                },
            },
        ]
    assert validate([a, b], "cgmlst").can_cluster
    b["pipeline_runs"][1]["pipeline_info"]["databases"][0]["version"] = "2"
    assert not validate([a, b], "cgmlst").can_cluster


def test_database_identity_is_available_without_declared_cgmlst_scheme():
    samples = [
        stored(sid, scheme=None, method="cgmlst", pipeline_run_id="run")
        for sid in ["a", "b"]
    ]
    for sample in samples:
        sample["pipeline_runs"] = [
            {
                "pipeline_run_id": "run",
                "pipeline_info": {
                    "databases": [
                        {"software": "chewbbaca", "name": "db", "version": "1"}
                    ]
                },
            }
        ]
    assert validate(samples, "cgmlst").can_cluster
