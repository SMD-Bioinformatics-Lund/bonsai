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
