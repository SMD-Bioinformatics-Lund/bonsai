"""A group carries a slug that is used to reference it when uploading samples."""

import pytest
from bonsai_api.models.group import GroupCore, GroupInfoCreate
from pydantic import ValidationError


def test_create_requires_a_slug():
    with pytest.raises(ValidationError):
        GroupInfoCreate.model_validate({"display_name": "S. aureus"})


@pytest.mark.parametrize("slug", ["saureus", "s-aureus", "s_aureus_2"])
def test_create_accepts_slug(slug):
    assert GroupInfoCreate.model_validate({"group": slug, "display_name": "S. aureus"}).group == slug


@pytest.mark.parametrize("slug", ["S. aureus", "-saureus", "s aureus", "s"])
def test_create_rejects_non_slug(slug):
    with pytest.raises(ValidationError):
        GroupInfoCreate.model_validate({"group": slug, "display_name": "S. aureus"})


def test_core_keeps_slug_and_generated_id():
    core = GroupCore(group_id="01a0b4de-fe36-7702-849d-c1790d12e29e", group="saureus", display_name="S. aureus")
    assert (core.group, core.group_id[:5]) == ("saureus", "01a0b")
