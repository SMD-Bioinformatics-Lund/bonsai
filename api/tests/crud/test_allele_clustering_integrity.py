"""Regressions for allele interpretation, schema checks, and queued data."""

import asyncio
import csv
import io
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import mongomock
import pytest

from bonsai_api.crud.cluster import (
    TypingProfileAggregate,
    get_profile_scheme,
    get_typing_profiles,
    validate_typing_profiles,
)
from bonsai_api.exceptions import EntryNotFound
from bonsai_api.redis import allele_cluster
from bonsai_api.redis.models import MsTreeMethods


def profile(sample_id, alleles, scheme="example", label=None):
    return TypingProfileAggregate(
        sample_id=sample_id, typing_result=alleles, scheme=scheme, label=label
    )


async def records(rows):
    for row in rows:
        yield row


@pytest.mark.parametrize("method", ["mlst", "cgmlst"])
def test_getter_preserves_scalar_normalization_and_handles_missing_calls(method):
    calls = {
        "a": "1",
        "b": 2,
        "c": "*3",
        "d": "INF-4",
        "e": None,
        "f": ["1", "2"],
        "g": "partial",
        "h": "novel",
        "i": "LNF",
        "j": 0,
    }
    collection = SimpleNamespace(
        aggregate=AsyncMock(
            return_value=records(
                [
                    {"sample_id": "a", "typing_result": calls, "scheme": "example"},
                ]
            )
        )
    )
    result = asyncio.run(
        get_typing_profiles(
            SimpleNamespace(sample_collection=collection), ["a"], method
        )
    )
    assert result[0].allele_profile() == {
        "a": 1,
        "b": 2,
        "c": 3,
        "d": 4,
        "e": None,
        "f": None,
        "g": None,
        "h": None,
        "i": None,
        "j": None,
    }


def test_aggregation_retains_scheme_metadata_and_full_locus_set():
    collection = mongomock.MongoClient().db.samples
    collection.insert_one(
        {
            "sample_id": "a",
            "typing_result": [
                {
                    "software": "mlst",
                    "analysis_type": "mlst",
                    "status": "parsed",
                    "result": {"scheme": "ecoli", "alleles": {"x": "1", "y": None}},
                }
            ],
        }
    )

    async def aggregate(pipeline):
        # mongomock lacks $unset; these stages only remove temporary selection fields.
        return records(
            list(collection.aggregate([s for s in pipeline if "$unset" not in s]))
        )

    db = SimpleNamespace(sample_collection=SimpleNamespace(aggregate=aggregate))
    result = asyncio.run(get_typing_profiles(db, ["a"], "mlst"))
    assert result[0].scheme == "ecoli"
    assert result[0].typing_result == {"x": 1, "y": None}


@pytest.mark.parametrize("method", ["mlst", "cgmlst"])
def test_schemes_and_locus_sets_must_match(method):
    a = profile("a", {"x": 1, "y": 1})
    for b in [
        profile("b", {"x": 1, "y": 1}, "different"),
        profile("b", {"x": 1, "z": 1}),
    ]:
        validation = validate_typing_profiles([a, b], method)
        assert not validation.can_cluster
        assert "different" in validation.notice
    assert validate_typing_profiles(
        [a, profile("b", {"y": 2, "x": None})], method
    ).can_cluster


@pytest.mark.parametrize("method", ["mlst", "cgmlst"])
def test_unknown_scheme_is_not_assumed_compatible(method):
    validation = validate_typing_profiles(
        [
            profile("a", {"x": 1}, None),
            profile("b", {"x": 2}, None),
        ],
        method,
    )
    assert not validation.can_cluster
    assert "could not be verified" in validation.notice


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


def test_cgmlst_aggregation_retains_envelope_scheme_and_analysis_run():
    collection = mongomock.MongoClient().db.samples
    collection.insert_one(
        {
            "sample_id": "a",
            "typing_result": [
                {
                    "software": "chewbbaca",
                    "analysis_type": "other-analysis",
                    "result": {"alleles": {"wrong": 99}, "scheme": "wrong"},
                },
                {
                    "software": "chewbbaca",
                    "analysis_type": "cgmlst",
                    "status": "parsed",
                    "pipeline_run_id": "run-1",
                    "meta": {"scheme": "schema-A"},
                    "result": {"alleles": {"x": "1", "y": "LNF"}},
                },
            ],
            "pipeline_runs": [
                {
                    "pipeline_run_id": "run-1",
                    "pipeline_info": {
                        "databases": [
                            {
                                "software": "chewbbaca",
                                "name": "database-A",
                                "version": "v1",
                            },
                        ]
                    },
                }
            ],
        }
    )

    async def aggregate(pipeline):
        return records(
            list(collection.aggregate([s for s in pipeline if "$unset" not in s]))
        )

    result = asyncio.run(
        get_typing_profiles(
            SimpleNamespace(sample_collection=SimpleNamespace(aggregate=aggregate)),
            ["a"],
            "cgmlst",
        )
    )
    assert result[0].scheme == '["schema-A","database-A","v1"]'
    assert result[0].allele_profile() == {"x": 1, "y": None}


def test_no_overlap_is_rejected_instead_of_becoming_a_zero_distance():
    validation = validate_typing_profiles(
        [
            profile("a", {"x": 1, "y": None}),
            profile("b", {"x": None, "y": 1}),
        ],
        "mlst",
    )
    assert not validation.can_cluster
    assert "no jointly called loci" in validation.notice


def test_no_call_profiles_are_retained_as_unplaced_but_cannot_form_a_tree_alone():
    empty = profile("empty", {"x": 0, "y": None}, label="LAB-EMPTY")
    usable = profile("usable", {"x": 1, "y": 2})
    validation = validate_typing_profiles([usable, empty], "mlst")
    assert validation.can_cluster
    assert [sample.label for sample in validation.unplaced_samples] == ["LAB-EMPTY"]
    assert not validate_typing_profiles(
        [empty, profile("also-empty", {})], "mlst"
    ).can_cluster


def test_missing_database_samples_are_still_rejected():
    collection = SimpleNamespace(aggregate=AsyncMock(return_value=records([])))
    with pytest.raises(EntryNotFound):
        asyncio.run(
            get_typing_profiles(
                SimpleNamespace(sample_collection=collection), ["missing"], "mlst"
            )
        )


def queued_profiles(monkeypatch, profiles):
    enqueue = Mock(return_value=SimpleNamespace(id="job", worker_name="worker"))
    monkeypatch.setattr(
        allele_cluster,
        "redis",
        SimpleNamespace(allele=SimpleNamespace(enqueue=enqueue)),
    )
    allele_cluster.schedule_cluster_samples(profiles, MsTreeMethods.MSTREE_V2)
    return enqueue.call_args.kwargs


def test_export_keeps_last_locus_integer_calls_missing_markers_and_sample_accounting(
    monkeypatch,
):
    queued = queued_profiles(
        monkeypatch,
        [
            profile("a", {"g1": 0, "g2": 1, "g3": 1}),
            profile("b", {"g1": 1, "g2": 1, "g3": 2}),
            profile("empty", {"g1": None, "g2": 0, "g3": None}, label="LAB-EMPTY"),
        ],
    )
    assert list(csv.reader(io.StringIO(queued["profile"]), delimiter="\t")) == [
        ["sample_id", "allele:g1", "allele:g2", "allele:g3"],
        ["a", "-", "1", "1"],
        ["b", "1", "1", "2"],
    ]
    assert queued["sample_ids"] == ["a", "b"]
    assert queued["meta"]["unplaced_samples"] == [
        {
            "sample_id": "empty",
            "label": "LAB-EMPTY",
            "reason": "No usable allele calls are available.",
        }
    ]


def test_real_worker_compares_every_exported_locus(monkeypatch, tmp_path):
    worker = pytest.importorskip("allele_cluster_service.tasks")
    from allele_cluster_service import ms_trees
    from ete3 import Tree
    import copy
    import tempfile

    defaults = copy.deepcopy(ms_trees.params)
    monkeypatch.setattr(ms_trees, "params", defaults)
    defaults["n_proc"] = 1
    original_tempfile = tempfile.NamedTemporaryFile

    def local_tempfile(*args, **kwargs):
        kwargs["dir"] = str(tmp_path)
        return original_tempfile(*args, **kwargs)

    monkeypatch.setattr(ms_trees.tempfile, "NamedTemporaryFile", local_tempfile)
    calls = {"g1": 1, "g2": 1, "g3": 1, "ST": 1, "#locus": 1}
    for gene in calls:
        changed = dict(calls)
        changed[gene] = 2
        queued = queued_profiles(
            monkeypatch,
            [profile("a", calls), profile("b", changed)],
        )
        newick = worker.cluster(
            queued["profile"], queued["method"], queued["sample_ids"]
        )
        assert Tree(newick).get_distance("a", "b") == 1
