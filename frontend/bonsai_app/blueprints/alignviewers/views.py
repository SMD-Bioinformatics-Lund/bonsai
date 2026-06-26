"""Views for alignment browsers."""

import logging

from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required

from bonsai_app.config import settings

alignviewers_bp = Blueprint(
    "alignviewers",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/alignviewers/static",
)

LOG = logging.getLogger(__name__)


@alignviewers_bp.route("/samples/<sample_id>/igv", methods=["GET"])  # from case page
@alignviewers_bp.route(
    "/samples/<sample_id>/<analysis_id>/<variant_id>/igv", methods=["GET"]
)  # from variants page
@login_required
def igv_view(
    sample_id: str, analysis_id: str | None = None, variant_id: str | None = None
):
    """Visualize alignments using igv.js (https://github.com/igvteam/igv.js)."""
    if (analysis_id is None) != (variant_id is None):
        # one is set but not the other → invalid
        abort(400, "analysis_id and variant_id must be provided")

    return render_template(
        "igv_view.html",
        access_token=current_user.get_id(),
        api_url=settings.api_external_url,
        sample_id=sample_id,
        analysis_id=analysis_id,
        variant_id=variant_id,
    )
