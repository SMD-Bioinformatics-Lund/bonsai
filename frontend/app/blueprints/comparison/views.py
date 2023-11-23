"""Views for comparing multiple samples."""

from app.bonsai import TokenObject, get_samples_by_id
from flask import Blueprint, redirect, render_template, session, url_for
from flask_login import current_user, login_required

comparison_bp = Blueprint(
    "comparison",
    __name__,
    template_folder="template",
    static_folder="statis",
    static_url_path="/comparison",
)


@comparison_bp.route("/compare/resistance")
@login_required
def compare_res_page():
    """
    Compare resistance predictons for samples.

    Get sample ids as params
    """
    # if not valid token or if user is not admin
    if current_user.get_id() is None or not current_user.is_admin:
        return redirect(url_for("public.index"))

    token = TokenObject(**current_user.get_id())
    sample_ids = session["samples"]
    samples = get_samples_by_id(token, sample_ids=sample_ids, limit=0, skip=0)

    return render_template(
        "resistance_compare.html", title="Resistance", samples=samples
    )
