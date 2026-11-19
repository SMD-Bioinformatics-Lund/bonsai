"""Group membership navigation across the sample's shared sidebar."""

import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from bs4 import BeautifulSoup
from bonsai_libs.api_client.core.exceptions import NetworkError

from bonsai_app.blueprints.sample import views
from bonsai_app.extensions import login_manager


@pytest.fixture
def sample_groups_page(app, user_obj, monkeypatch):
    fixture = Path(__file__).parents[2] / "api/tests/data/test_ecoli_1.json"
    sample = json.loads(fixture.read_text())
    sample.update(
        groups=["group-z", "group-a", "group-b", "group-a"],
        species_prediction=[], typing_result=[], element_type_result=[], qc_result=[],
        metadata=[], reference_genome_id=None,
        qc_status={"status": "unprocessed", "action": None, "comment": ""},
    )
    groups = [
        SimpleNamespace(group_id="group-z", display_name="z" * 160),
        SimpleNamespace(group_id="unrelated", display_name="Other samples"),
        SimpleNamespace(group_id="group-b", display_name="Beta <team>"),
        SimpleNamespace(group_id="group-a", display_name="alpha"),
    ]
    api = SimpleNamespace(
        get_sample_by_id=Mock(side_effect=lambda **kwargs: deepcopy(sample)),
        get_groups=Mock(return_value=groups),
        get_antibiotics=Mock(return_value=[]),
        get_variant_rejection_reasons=Mock(return_value=[]),
    )
    monkeypatch.setattr(views, "get_api_client", lambda: api)
    monkeypatch.setitem(login_manager.__dict__, "_user_callback", lambda _: user_obj)
    app.config["TESTING"] = True
    with app.test_client(user=user_obj) as client:
        yield client, sample, api


@pytest.mark.parametrize("page", ["", "/resistance/variants", "/metadata"])
@pytest.mark.parametrize("from_group", [False, True])
def test_sidebar_links_all_memberships_in_name_order(sample_groups_page, page, from_group):
    client, sample, api = sample_groups_page
    query = "?group_id=group-b" if from_group else ""

    response = client.get(f"/sample/{sample['sample_id']}{page}{query}")

    assert response.status_code == 200
    dom = BeautifulSoup(response.data, "html.parser")
    sidebar = dom.select_one(".br-sidebar")
    assert [heading.get_text(strip=True) for heading in sidebar.find_all("h6")][:3] == [
        "Metadata", "Groups", "Reports",
    ]
    links = sidebar.select('nav[aria-label="Sample groups"] a')
    assert [(link.get_text(strip=True), link["href"]) for link in links] == [
        ("alpha", "/groups/group-a"),
        ("Beta <team>", "/groups/group-b"),
        ("z" * 160, "/groups/group-z"),
    ]
    assert links[1].find("team") is None
    assert "Other samples" not in sidebar.get_text()
    api.get_groups.assert_called_once_with()


@pytest.mark.parametrize("page", ["", "/resistance/variants", "/metadata"])
def test_sidebar_distinguishes_no_memberships_without_a_group_lookup(sample_groups_page, page):
    client, sample, api = sample_groups_page
    sample["groups"] = []

    response = client.get(f"/sample/{sample['sample_id']}{page}")

    assert response.status_code == 200
    dom = BeautifulSoup(response.data, "html.parser")
    groups = dom.select_one('nav[aria-label="Sample groups"]')
    assert "No group memberships." in groups.get_text()
    assert "Unable to load" not in groups.get_text()
    assert not groups.find_all("a")
    api.get_groups.assert_not_called()


@pytest.mark.parametrize("page", ["", "/resistance/variants", "/metadata"])
def test_group_lookup_failure_keeps_the_sample_page_available(sample_groups_page, page):
    client, sample, api = sample_groups_page
    api.get_groups.side_effect = NetworkError("API unavailable")

    response = client.get(f"/sample/{sample['sample_id']}{page}")

    assert response.status_code == 200
    dom = BeautifulSoup(response.data, "html.parser")
    groups = dom.select_one('nav[aria-label="Sample groups"]')
    assert "Unable to load group memberships." in groups.get_text()
    assert "No group memberships." not in groups.get_text()
    assert not groups.find_all("a")


@pytest.mark.parametrize("page", ["", "/resistance/variants", "/metadata"])
@pytest.mark.parametrize("from_group", [False, True])
def test_non_admin_keeps_public_links_with_private_memberships(
    sample_groups_page, user_obj, page, from_group,
):
    client, sample, api = sample_groups_page
    user_obj.roles = ["user"]
    sample["groups"] = ["private-group", "group-b", "group-a", "group-a"]
    api.get_groups.return_value = [
        group for group in api.get_groups.return_value if group.group_id != "group-z"
    ]
    query = "?group_id=group-b" if from_group else ""

    response = client.get(f"/sample/{sample['sample_id']}{page}{query}")

    assert response.status_code == 200
    dom = BeautifulSoup(response.data, "html.parser")
    groups = dom.select_one('nav[aria-label="Sample groups"]')
    assert [(link.get_text(strip=True), link["href"]) for link in groups.find_all("a")] == [
        ("alpha", "/groups/group-a"),
        ("Beta <team>", "/groups/group-b"),
    ]
    assert "Unable to load" not in groups.get_text()
    assert "No group memberships." not in groups.get_text()
    assert "private-group" not in str(groups)
    assert "Other samples" not in groups.get_text()
    api.get_groups.assert_called_once_with()


@pytest.mark.parametrize("page", ["", "/resistance/variants", "/metadata"])
@pytest.mark.parametrize("empty_listing", [False, True])
def test_non_admin_with_only_hidden_memberships_has_no_visible_links(
    sample_groups_page, user_obj, page, empty_listing,
):
    client, sample, api = sample_groups_page
    user_obj.roles = ["user"]
    sample["groups"] = ["private-group"]
    if empty_listing:
        api.get_groups.return_value = []

    response = client.get(f"/sample/{sample['sample_id']}{page}")

    assert response.status_code == 200
    dom = BeautifulSoup(response.data, "html.parser")
    groups = dom.select_one('nav[aria-label="Sample groups"]')
    assert "No visible group memberships." in groups.get_text()
    assert "Unable to load" not in groups.get_text()
    assert "No group memberships." not in groups.get_text()
    assert not groups.find_all("a")
    assert "private-group" not in str(groups)
    api.get_groups.assert_called_once_with()
