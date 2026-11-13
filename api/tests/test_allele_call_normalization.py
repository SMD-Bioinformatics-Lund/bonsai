"""Allele values must keep the same meaning during preparation and export."""

import asyncio
import csv
import io
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from bonsai_api.crud.cluster import TypingProfileAggregate, get_typing_profiles
from bonsai_api.exceptions import InvalidDataFormat
from bonsai_api.redis import allele_cluster
from bonsai_api.redis.models import MsTreeMethods


async def records(rows):
    for row in rows:
        yield row


def database(calls):
    return SimpleNamespace(
        sample_collection=SimpleNamespace(
            aggregate=AsyncMock(
                return_value=records(
                    [
                        {
                            "sample_id": "a",
                            "external_sample_id": "LAB-A",
                            "typing_result": calls,
                        }
                    ]
                )
            )
        )
    )


@pytest.mark.parametrize("method", ["mlst", "cgmlst"])
def test_scalar_compatibility_and_missing_calls(method):
    calls = {
        "int": 1,
        "str": "2",
        "star": "*3",
        "novel": "INF-4",
        "null": None,
        "ambiguous": ["1", "2"],
        "partial": "partial",
        "new": "novel",
        "LNF": "LNF",
        "zero": 0,
        "zero_str": "0",
        "bool": True,
        "blank": "",
    }
    result = asyncio.run(get_typing_profiles(database(calls), ["a"], method))[0]
    assert result.allele_profile() == {
        "int": 1,
        "str": 2,
        "star": 3,
        "novel": 4,
        **{
            key: None
            for key in [
                "null",
                "ambiguous",
                "partial",
                "new",
                "LNF",
                "zero",
                "zero_str",
                "bool",
                "blank",
            ]
        },
    }


@pytest.mark.parametrize("bad", [{"a": {}}, {"a": 1.0}, ["bad-profile"]])
def test_malformed_data_is_a_validation_error(bad):
    with pytest.raises(InvalidDataFormat, match="Invalid mlst allele"):
        asyncio.run(get_typing_profiles(database(bad), ["a"], "mlst"))


def test_missing_alleles_do_not_promote_real_alleles_to_floats(monkeypatch):
    enqueue = Mock(return_value=SimpleNamespace(id="job", worker_name="worker"))
    monkeypatch.setattr(
        allele_cluster,
        "redis",
        SimpleNamespace(allele=SimpleNamespace(enqueue=enqueue)),
    )
    allele_cluster.schedule_cluster_samples(
        [
            TypingProfileAggregate(
                sample_id="a", typing_result={"x": None, "y": 1, "last": 0}
            ),
            TypingProfileAggregate(
                sample_id="b", typing_result={"x": 1, "y": 1, "last": 2}
            ),
        ],
        MsTreeMethods.MSTREE_V2,
    )
    rows = list(
        csv.reader(io.StringIO(enqueue.call_args.kwargs["profile"]), delimiter="\t")
    )
    assert rows[1] == ["a", "-", "1", "-"]
    assert rows[2] == ["b", "1", "1", "2"]
    assert ".0" not in enqueue.call_args.kwargs["profile"]
