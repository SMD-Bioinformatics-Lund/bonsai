"""Tests for validating genomic resource paths."""

import pytest

from bonsai_api.exceptions import GenomeResourceError
from bonsai_api.io import resolve_resource_path, to_relative_resource


@pytest.fixture()
def trees(tmp_path):
    """Create an access tree whose files may link into a separate backup tree."""
    backup = tmp_path / "backup" / "saureus" / "vcf"
    backup.mkdir(parents=True)
    target = backup / "S1_freebayes.vcf"
    target.write_text("x")

    access = tmp_path / "access"
    vcf_dir = access / "saureus" / "vcf"
    vcf_dir.mkdir(parents=True)
    (vcf_dir / "S1_freebayes.vcf").symlink_to(target)
    (vcf_dir / "S1_plain.vcf").write_text("x")
    return access, tmp_path / "backup"


def test_relative_real_file(trees):
    access, _ = trees
    assert to_relative_resource("saureus/vcf/S1_plain.vcf", access) == (
        "saureus/vcf/S1_plain.vcf"
    )


def test_relative_symlink_to_outside_target(trees):
    access, _ = trees
    assert to_relative_resource("saureus/vcf/S1_freebayes.vcf", access) == (
        "saureus/vcf/S1_freebayes.vcf"
    )


@pytest.mark.parametrize("name", ["S1_plain.vcf", "S1_freebayes.vcf"])
def test_absolute_path_inside_base_is_stored_relative(trees, name):
    access, _ = trees
    absolute = str(access / "saureus" / "vcf" / name)
    assert to_relative_resource(absolute, access) == f"saureus/vcf/{name}"


def test_absolute_path_outside_base_rejected(trees):
    access, backup = trees
    with pytest.raises(GenomeResourceError, match="Outside allowed directory"):
        to_relative_resource(backup / "saureus" / "vcf" / "S1_freebayes.vcf", access)


def test_traversal_rejected(trees):
    access, _ = trees
    with pytest.raises(GenomeResourceError, match=r"\.\."):
        to_relative_resource("saureus/../../backup/saureus/vcf/S1_freebayes.vcf", access)


def test_absolute_traversal_rejected(trees):
    access, _ = trees
    with pytest.raises(GenomeResourceError):
        to_relative_resource(access / ".." / "backup" / "saureus", access)


def test_dangling_symlink_not_found(trees):
    access, _ = trees
    (access / "saureus" / "vcf" / "gone.vcf").symlink_to(access / "missing.vcf")
    with pytest.raises(GenomeResourceError, match="not found"):
        to_relative_resource("saureus/vcf/gone.vcf", access)


def test_served_path_stays_under_base(trees):
    access, _ = trees
    served = resolve_resource_path("saureus/vcf/S1_freebayes.vcf", access)
    assert access in served.parents
    assert served.read_text() == "x"
