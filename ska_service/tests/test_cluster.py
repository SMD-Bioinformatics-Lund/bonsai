"""SNV trees preserve the selected records even when file and sequence names repeat."""

import io
import random
import shutil
import subprocess
from collections import Counter
from pathlib import Path

from Bio import Phylo
import pytest

from ska_service import tasks

SAMPLE_IDS = [
    "01991d8e-5d6d-7000-8000-000000000001",
    "01991d8e-5d6d-7000-8000-000000000002",
    "01991d8e-5d6d-7000-8000-000000000003",
]


def records(tmp_path):
    return [
        {
            "sample_id": sid,
            "external_sample_id": "LAB-123",
            "ska_index": str(tmp_path / f"run-{number}" / "LAB-123.skf"),
        }
        for number, sid in enumerate(SAMPLE_IDS)
    ]


@pytest.mark.skipif(shutil.which("ska") is None, reason="requires SKA2 executable")
@pytest.mark.parametrize(
    "mutations",
    [([], [100], [100, 400, 700, 1000]), ([], [], [])],
    ids=["different-genomes", "identical-genomes"],
)
def test_native_clustering_with_repeated_filenames_and_sequence_names(
    tmp_path, mutations
):
    """The pinned SKA binary must retain row order and distinct biological distances."""
    rng = random.Random(17)
    reference = "".join(rng.choices("ACGT", k=2000))
    indexes = records(tmp_path)
    for record, positions in zip(indexes, mutations):
        path = Path(record["ska_index"])
        path.parent.mkdir()
        bases = list(reference)
        for position in positions:
            bases[position] = "C" if bases[position] == "A" else "A"
        fasta = path.with_suffix(".fasta")
        fasta.write_text(">same-contig-name\n" + "".join(bases) + "\n")
        subprocess.run(
            ["ska", "build", "-k", "31", "-o", str(path), str(fasta)],
            check=True,
            capture_output=True,
        )
    original_files = [Path(record["ska_index"]).read_bytes() for record in indexes]

    newick = tasks.cluster(indexes)

    tree = Phylo.read(io.StringIO(newick), "newick")
    assert Counter(leaf.name for leaf in tree.get_terminals()) == Counter(SAMPLE_IDS)
    if any(mutations):
        closest = tree.common_ancestor(SAMPLE_IDS[:2])
        assert {leaf.name for leaf in closest.get_terminals()} == set(SAMPLE_IDS[:2])
    else:
        assert tree.total_branch_length() == 0
    assert [
        Path(record["ska_index"]).read_bytes() for record in indexes
    ] == original_files


def test_repeated_names_are_assigned_by_input_record(tmp_path, monkeypatch):
    indexes = records(tmp_path)
    alignment = tmp_path / "merged.fasta"
    alignment.write_text(">LAB-123\nAAAA\n>LAB-123\nAAAC\n>LAB-123\nAACC\n")
    monkeypatch.setattr(tasks.ska, "resolve_index_path", lambda p, *a, **kw: Path(p))
    monkeypatch.setattr(tasks.ska, "sample_count", lambda p: 1, raising=False)
    monkeypatch.setattr(tasks.ska, "merge", lambda *a, **kw: tmp_path / "merged.skf")
    monkeypatch.setattr(tasks.ska, "align", lambda *a, **kw: alignment)

    tree = Phylo.read(io.StringIO(tasks.cluster(indexes)), "newick")

    assert Counter(leaf.name for leaf in tree.get_terminals()) == Counter(SAMPLE_IDS)


def test_multi_sample_index_is_rejected_before_merging(tmp_path, monkeypatch):
    indexes = records(tmp_path)
    monkeypatch.setattr(tasks.ska, "resolve_index_path", lambda p, *a, **kw: Path(p))
    monkeypatch.setattr(tasks.ska, "sample_count", lambda p: 2, raising=False)

    def unexpected_merge(*args, **kwargs):
        pytest.fail("A multi-sample index must be rejected before merging")

    monkeypatch.setattr(tasks.ska, "merge", unexpected_merge)
    with pytest.raises(ValueError, match="exactly one sample"):
        tasks.cluster(indexes)


def test_incomplete_alignment_is_rejected(tmp_path, monkeypatch):
    alignment = tmp_path / "partial.fasta"
    alignment.write_text(">LAB-123\nAAAA\n>LAB-123\nAAAC\n")
    monkeypatch.setattr(tasks.ska, "resolve_index_path", lambda p, *a, **kw: Path(p))
    monkeypatch.setattr(tasks.ska, "sample_count", lambda p: 1, raising=False)
    monkeypatch.setattr(tasks.ska, "merge", lambda *a, **kw: tmp_path / "merged.skf")
    monkeypatch.setattr(tasks.ska, "align", lambda *a, **kw: alignment)
    with pytest.raises(ValueError, match="one sequence per selected sample"):
        tasks.cluster(records(tmp_path))
