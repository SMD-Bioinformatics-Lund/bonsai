"""Hidden comments must not contribute to sample-table badges or tooltips."""

import pytest
from bs4 import BeautifulSoup


@pytest.mark.parametrize("visible_count,hidden_count", [(0, 0), (0, 2), (1, 1), (2, 1)])
def test_comment_badge_counts_only_comments_in_tooltip(app, visible_count, hidden_count):
    comments = [
        {"comment": f"Visible comment {i}", "username": "reviewer", "displayed": True}
        for i in range(visible_count)
    ] + [
        {"comment": f"Removed comment {i}", "username": "reviewer", "displayed": False}
        for i in range(hidden_count)
    ]
    template = app.jinja_env.from_string(
        '{% from "cell_fmt.html" import comments_renderer %}{{ comments_renderer(comments) }}'
    )

    html = template.render(comments=comments)

    cell = BeautifulSoup(html, "html.parser").find("td")
    badge = cell.find("span", class_="badge")
    if visible_count:
        assert badge.get_text(strip=True) == str(visible_count)
        tooltip = badge["data-bs-title"]
        for i in range(visible_count):
            assert f"Visible comment {i}" in tooltip
    else:
        assert badge is None
    assert "Removed comment" not in html


def test_removing_final_comment_removes_badge(app):
    template = app.jinja_env.from_string(
        '{% from "cell_fmt.html" import comments_renderer %}{{ comments_renderer(comments) }}'
    )
    comments = [{"comment": "Review note", "username": "reviewer", "displayed": True}]
    assert "Review note" in template.render(comments=comments)

    comments[0]["displayed"] = False

    html = template.render(comments=comments)
    assert BeautifulSoup(html, "html.parser").find("span", class_="badge") is None
    assert "Review note" not in html


def test_comment_tooltip_preserves_literal_text(app):
    template = app.jinja_env.from_string(
        '{% from "cell_fmt.html" import comments_renderer %}{{ comments_renderer(comments) }}'
    )
    comment = {"comment": '<Review> & "notes"', "username": "<Reviewer>", "displayed": True}
    html = template.render(comments=[comment])
    badge = BeautifulSoup(html, "html.parser").find("span", class_="badge")
    tooltip = BeautifulSoup(badge["data-bs-title"], "html.parser")

    assert [p.get_text() for p in tooltip.find_all("p")] == [
        comment["comment"],
        f'- {comment["username"]}',
    ]
